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

from conf import elasticsearch_config, indexes_to_monitor, polling_interval
from notificators_setup import notificators
from logger import logger


class AlertPollerService:
    """
    Service that polls Elasticsearch for unprocessed alerts and sends notifications.
    """
    
    def __init__(self):
        self.running = False
        self.es_client: Optional[Elasticsearch] = None
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
    
    def _connect_elasticsearch(self) -> bool:
        """
        Establish connection to Elasticsearch.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Build connection to Elasticsearch
            self.es_client = Elasticsearch(
                hosts=[{
                    "host": elasticsearch_config["host"],
                    "port": elasticsearch_config["port"],
                    "scheme": "http"
                }],
                basic_auth=(elasticsearch_config["username"], elasticsearch_config["password"]),
                verify_certs=elasticsearch_config["verify_certs"],
                request_timeout=elasticsearch_config["timeout"]
            )
            
            # Test connection
            info = self.es_client.info()
            logger.info(f"Successfully connected to Elasticsearch: {info['version']['number']}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            logger.exception(e)
            return False
    
    def _fetch_unprocessed_alerts(self, index: str) -> list:
        """
        Fetch all unprocessed alerts from the specified index.
        
        Args:
            index: The Elasticsearch index to query
            
        Returns:
            list: List of unprocessed alert documents with their IDs
        """
        if not self.es_client:
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
                    {"timestamp": {"order": "asc"}}  # Process oldest first
                ],
                "size": 100  # Batch size
            }
            
            response = self.es_client.search(index=index, body=query)
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
    
    def _mark_as_processed(self, index: str, doc_id: str) -> bool:
        """
        Mark an alert document as processed.
        
        Args:
            index: The Elasticsearch index
            doc_id: The document ID
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if not self.es_client:
            return False
        
        try:
            self.es_client.update(
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
        notificator_id = index_config["notificator_id"]
        
        # Get the notificator
        notificator = notificators.get(notificator_id)
        if not notificator:
            logger.error(f"Notificator '{notificator_id}' not found for index '{index}'")
            return 0
        
        # Fetch unprocessed alerts
        alerts = self._fetch_unprocessed_alerts(index)
        
        processed_count = 0
        for alert in alerts:
            # Check if we should stop
            if not self.running:
                logger.info("Shutdown requested, stopping alert processing")
                break
            
            doc_id = alert["id"]
            source = alert["source"]
            message = source.get("message", "No message provided")
            timestamp = source.get("timestamp", "Unknown time")
            
            # Format the notification message
            notification_message = (
                f"**Alert from index: {index}**\n"
                f"**Time:** {timestamp}\n\n"
                f"{message}"
            )
            
            try:
                # Send notification
                notificator.notify(notification_message)
                logger.info(f"Notification sent for alert '{doc_id}' from index '{index}'")
                
                # Mark as processed
                if self._mark_as_processed(alert["index"], doc_id):
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
        
        # Connect to Elasticsearch
        if not self._connect_elasticsearch():
            logger.error("Failed to establish initial connection to Elasticsearch. Exiting.")
            sys.exit(1)
        
        self.running = True
        
        while self.running:
            try:
                # Check Elasticsearch connection
                if not self.es_client or not self.es_client.ping():
                    logger.warning("Lost connection to Elasticsearch. Attempting to reconnect...")
                    if not self._connect_elasticsearch():
                        logger.error("Failed to reconnect. Will retry on next poll cycle.")
                        time.sleep(polling_interval)
                        continue
                
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
        if self.es_client:
            self.es_client.close()
            logger.info("Elasticsearch connection closed")
        
        logger.info("Alert Poller Service stopped gracefully")


def main():
    """Entry point for the service."""
    service = AlertPollerService()
    service.run()


if __name__ == "__main__":
    main()