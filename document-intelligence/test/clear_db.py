#!/usr/bin/env python3
"""
Manual script to clear the Weaviate vector database.
Run this script to delete all classes/collections from the database.
"""

import weaviate
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_vector_database():
    """Clear all data from the Weaviate vector database."""
    try:
        # Connect to Weaviate (v4 client)
        client = weaviate.connect_to_local(host="localhost", port=28947)
        
        logger.info("Connected to Weaviate database")
        
        # Get all collections
        collections = client.collections.list_all()
        
        if not collections:
            logger.info("No collections found in the database - already empty")
            client.close()
            return
        
        logger.info(f"Found {len(collections)} collections to delete")
        
        # Delete each collection
        for collection_name in collections:
            logger.info(f"Deleting collection: {collection_name}")
            
            try:
                client.collections.delete(collection_name)
                logger.info(f"✅ Successfully deleted collection: {collection_name}")
            except Exception as e:
                logger.error(f"❌ Failed to delete collection {collection_name}: {str(e)}")
        
        # Verify deletion
        final_collections = client.collections.list_all()
        
        if not final_collections:
            logger.info("🎉 Database successfully cleared - no collections remain")
        else:
            logger.warning(f"⚠️  {len(final_collections)} collections still remain after deletion")
        
        client.close()
            
    except Exception as e:
        logger.error(f"❌ Error connecting to Weaviate or clearing database: {str(e)}")
        logger.error("Make sure Weaviate is running on localhost:28947")

if __name__ == "__main__":
    logger.info("Starting manual database clearing...")
    clear_vector_database()
    logger.info("Database clearing completed")