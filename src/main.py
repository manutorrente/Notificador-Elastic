"""
Elasticsearch Alert Notificator Service

This script polls Elasticsearch indexes for unprocessed alert documents
and sends notifications using the configured notificators.

Designed to run as a Linux systemd service with graceful shutdown handling.
"""

import signal
import sys
import time
from datetime import datetime
from typing import Optional

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError, TransportError

from conf import elasticsearch_connections, indexes_to_monitor, polling_interval
from notificators_setup import notificators
from logger import logger
from utils import calculate_downtime


class AlertPollerService:
    """
    Service that polls Elasticsearch for unprocessed alerts and sends notifications.
    """
    
    def __init__(self):
        self.running = False
        self.es_clients: dict[str, Elasticsearch] = {}
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name} signal. Initiating graceful shutdown...")
        self.running = False
    
    def _connect_elasticsearch(self, connection_name: Optional[str] = None) -> bool:
        """
        Establish connection(s) to Elasticsearch.
        
        Args:
            connection_name: If provided, connect only to this specific connection.
                             If None, connect to all configured connections.
        
        Returns:
            bool: True if all requested connections successful, False otherwise
        """
        targets = {connection_name: elasticsearch_connections[connection_name]} if connection_name else elasticsearch_connections
        all_ok = True

        for name, config in targets.items():
            try:
                client = Elasticsearch(
                    hosts=[{
                        "host": config["host"],
                        "port": config["port"],
                        "scheme": "http"
                    }],
                    basic_auth=(config["username"], config["password"]),
                    verify_certs=config["verify_certs"],
                    request_timeout=config["timeout"]
                )

                info = client.info()
                logger.info(f"Successfully connected to Elasticsearch '{name}': {info['version']['number']}")
                self.es_clients[name] = client

            except Exception as e:
                logger.error(f"Failed to connect to Elasticsearch '{name}': {e}")
                logger.exception(e)
                all_ok = False

        return all_ok
    
    def _fetch_unprocessed_alerts(self, index: str, connection_name: str) -> list:
        """
        Fetch all unprocessed alerts from the specified index.
        
        Args:
            index: The Elasticsearch index to query
            connection_name: The name of the Elasticsearch connection to use
            
        Returns:
            list: List of unprocessed alert documents with their IDs
        """
        es_client = self.es_clients.get(connection_name)
        if not es_client:
            logger.error(f"No Elasticsearch client for connection '{connection_name}'")
            return []
        
        try:
            # Query for documents where processed = false
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"processed": False}}
                        ]
                    }
                },
                "sort": [
                    {"@timestamp": {"order": "asc"}}  # Process oldest first
                ],
                "size": 100  # Batch size
            }
            
            response = es_client.search(index=index, body=query)
            hits = response.get("hits", {}).get("hits", [])
            
            alerts = []
            for hit in hits:
                alerts.append({
                    "id": hit["_id"],
                    "index": hit["_index"],
                    "source": hit["_source"]
                })
            
            if alerts:
                logger.debug(f"Found {len(alerts)} unprocessed alerts in index '{index}'")
            
            return alerts
            
        except NotFoundError:
            logger.warning(f"Index '{index}' not found")
            return []
        except Exception as e:
            logger.error(f"Error fetching alerts from index '{index}': {e}")
            return []
    
    def _mark_as_processed(self, index: str, doc_id: str, connection_name: str) -> bool:
        """
        Mark an alert document as processed.
        
        Args:
            index: The Elasticsearch index
            doc_id: The document ID
            connection_name: The name of the Elasticsearch connection to use
            
        Returns:
            bool: True if update successful, False otherwise
        """
        es_client = self.es_clients.get(connection_name)
        if not es_client:
            logger.error(f"No Elasticsearch client for connection '{connection_name}'")
            return False
        
        try:
            es_client.update(
                index=index,
                id=doc_id,
                body={
                    "doc": {
                        "processed": True,
                        "processed_at": datetime.utcnow().isoformat()
                    }
                }
            )
            logger.debug(f"Marked document '{doc_id}' in index '{index}' as processed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark document '{doc_id}' as processed: {e}")
            return False
    
    def _process_alerts_for_index(self, index_config: dict) -> int:
        """
        Process all unprocessed alerts for a specific index.
        
        Args:
            index_config: Configuration dict with 'index' and 'notificator_id'
            
        Returns:
            int: Number of alerts successfully processed
        """
        index = index_config["index"]
        default_notificator_id = index_config["notificator_id"]
        connection_name = index_config["connection"]
        
        # Fetch unprocessed alerts
        alerts = self._fetch_unprocessed_alerts(index, connection_name)
        
        processed_count = 0
        for alert in alerts:
            # Check if we should stop
            if not self.running:
                logger.info("Shutdown requested, stopping alert processing")
                break
            
            doc_id = alert["id"]
            source = alert["source"]
            
            # Check for notificator override in the document, fallback to default
            notificator_id = source.get("notificator_override", default_notificator_id)
            
            # Get the notificator
            notificator = notificators.get(notificator_id)
            if not notificator:
                logger.error(f"Notificator '{notificator_id}' not found for alert '{doc_id}' in index '{index}'")
                continue
            
            message = source.get("message", "No message provided")
            timestamp = source.get("@timestamp", "Unknown time")
            
            # Extract config from document if present
            alert_config = source.get("config", {})
            
            # Pre-calculate downtime if status is up and we have start/end times
            if alert_config.get("status", "").lower() == "up":
                alert_start = alert_config.get("alert_start")
                alert_end = alert_config.get("alert_end")
                if alert_start and alert_end:
                    try:
                        alert_config["downtime"] = calculate_downtime(alert_start, alert_end)
                    except Exception as e:
                        logger.warning(f"Failed to calculate downtime for alert '{doc_id}': {e}")
            
            # Format the notification message
            notification_message = (
                f"**Alert from index: {index}**\n"
                f"**Time:** {timestamp}\n\n"
                f"{message}"
            )
            
            try:
                # Send notification with config
                notificator.notify(notification_message, **alert_config)
                logger.info(f"Notification sent for alert '{doc_id}' from index '{index}' using notificator '{notificator_id}'")
                
                # Mark as processed
                if self._mark_as_processed(alert["index"], doc_id, connection_name):
                    processed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process alert '{doc_id}': {e}")
                continue
        
        return processed_count
    
    def run(self):
        """
        Main service loop.
        Polls Elasticsearch for unprocessed alerts and sends notifications.
        """
        logger.info("Starting Alert Poller Service...")
        logger.info(f"Polling interval: {polling_interval} seconds")
        logger.info(f"Monitoring {len(indexes_to_monitor)} index(es)")
        logger.info(f"Configured Elasticsearch connections: {', '.join(elasticsearch_connections.keys())}")
        
        # Connect to all Elasticsearch instances
        if not self._connect_elasticsearch():
            logger.error("Failed to establish initial connection to one or more Elasticsearch instances. Exiting.")
            sys.exit(1)
        
        self.running = True
        
        while self.running:
            try:
                # Check Elasticsearch connections and reconnect if needed
                for conn_name, client in list(self.es_clients.items()):
                    try:
                        if not client.ping():
                            raise ConnectionError(f"Ping failed for '{conn_name}'")
                    except Exception:
                        logger.warning(f"Lost connection to Elasticsearch '{conn_name}'. Attempting to reconnect...")
                        self._connect_elasticsearch(conn_name)
                
                # Process alerts for each configured index
                total_processed = 0
                for index_config in indexes_to_monitor:
                    if not self.running:
                        break
                    processed = self._process_alerts_for_index(index_config)
                    total_processed += processed
                
                if total_processed > 0:
                    logger.info(f"Processed {total_processed} alert(s) in this polling cycle")
                
            except ConnectionError as e:
                logger.error(f"Elasticsearch connection error: {e}")
            except TransportError as e:
                logger.error(f"Elasticsearch transport error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during polling: {e}")
                logger.exception(e)
            
            # Wait for next poll cycle, but check for shutdown signal periodically
            if self.running:
                # Sleep in small increments to allow for faster shutdown response
                sleep_increment = 1  # Check every second
                for _ in range(polling_interval):
                    if not self.running:
                        break
                    time.sleep(sleep_increment)
        
        # Cleanup
        logger.info("Shutting down Alert Poller Service...")
        for conn_name, client in self.es_clients.items():
            try:
                client.close()
                logger.info(f"Elasticsearch connection '{conn_name}' closed")
            except Exception as e:
                logger.error(f"Error closing Elasticsearch connection '{conn_name}': {e}")
        
        logger.info("Alert Poller Service stopped gracefully")


def main():
    """Entry point for the service."""
    service = AlertPollerService()
    service.run()


if __name__ == "__main__":
    main()