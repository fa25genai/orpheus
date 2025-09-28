import sys
import os
from pathlib import Path
import logging
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from docint_app.services.pdf_upload_service import PDFUploadService
from docint_app.services.ingestion_service import IngestionService
from docint_app.services.retrieval_service import RetrievalService
from docint_app.vectorstore.weaviate_graph_store import WeaviateGraphStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetrievalQualityTest:
    def __init__(self):
        self.pdf_upload_service = PDFUploadService()
        self.ingestion_service = IngestionService()
        self.retrieval_service = RetrievalService()
        self.graph_store = WeaviateGraphStore()

    def upload_and_store_pdfs(self):
        """Upload and store PDF files from the test directory."""
        test_dir = Path(__file__).parent
        pdf_files = list(test_dir.glob("*.pdf"))
        
        logger.info(f"Found {len(pdf_files)} PDF files in test directory")
        
        for pdf_file in pdf_files:
            logger.info(f"Processing {pdf_file.name}")
            
            # Upload PDF
            course_id = pdf_file.stem
            with open(pdf_file, "rb") as f:
                pdf_data = f.read()
            
            upload_response = self.pdf_upload_service.upload_pdf(
                course_id=course_id,
                pdf_data=pdf_data
            )
            
            # Ingest the uploaded PDF
            self.ingestion_service.ingest_lecture(
                course_id=course_id,
                pdf_path=upload_response.file_path
            )
            
            logger.info(f"Successfully processed {pdf_file.name}")

    def test_queries(self):
        """Test different queries and evaluate their relevance."""
        test_queries = [
            {
                "query": "What are the main differences between compiled and interpreted programming languages?",
                "expected_relevant": True,
                "topic": "Programming Languages - Compilation vs Interpretation"
            },
            {
                "query": "Explain what domain specific languages are and their use cases",
                "expected_relevant": True,
                "topic": "Domain Specific Languages"
            },
            {
                "query": "How to create and analyze syntax trees in programming languages?",
                "expected_relevant": True,
                "topic": "Syntax Trees"
            },
            {
                "query": "What are regular expressions and how do they work in programming languages?",
                "expected_relevant": True,
                "topic": "Regular Expressions"
            },
            {
                "query": "Explain inheritance and polymorphism in object-oriented programming",
                "expected_relevant": False,
                "topic": "OOP Concepts (Should Not Match)"
            }
        ]

        results = []
        
        for query_info in test_queries:
            query = query_info["query"]
            logger.info(f"\nTesting query: {query}")
            logger.info(f"Topic: {query_info['topic']}")
            logger.info(f"Expected to find relevant results: {query_info['expected_relevant']}")
            
            # Get results from retrieval service
            response = self.retrieval_service.retrieve_data_for_generation(query)
            
            # Log results
            logger.info(f"Number of results: {len(response.text_objects)}")
            
            for i, text_obj in enumerate(response.text_objects):
                logger.info(f"\nResult {i+1}:")
                logger.info(f"Content: {text_obj.content[:200]}...")  # Show first 200 chars
                logger.info(f"Similarity Score: {text_obj.similarity_score}")
                logger.info(f"Source: {text_obj.source}")
                
                results.append({
                    "query": query,
                    "topic": query_info["topic"],
                    "expected_relevant": query_info["expected_relevant"],
                    "content": text_obj.content,
                    "similarity_score": text_obj.similarity_score,
                    "source": text_obj.source
                })
            
            logger.info("-" * 80)

        return results

    def analyze_results(self, results):
        """Analyze the quality of retrieval results."""
        logger.info("\nRESULTS ANALYSIS")
        logger.info("=" * 80)
        
        # Aggregate metrics by query
        for query_info in set((r["query"], r["topic"]) for r in results):
            query_results = [r for r in results if r["query"] == query_info[0]]
            
            logger.info(f"\nQuery: {query_info[0]}")
            logger.info(f"Topic: {query_info[1]}")
            logger.info(f"Number of results: {len(query_results)}")
            
            if query_results:
                avg_similarity = sum(r["similarity_score"] for r in query_results) / len(query_results)
                max_similarity = max(r["similarity_score"] for r in query_results)
                
                logger.info(f"Average similarity score: {avg_similarity:.3f}")
                logger.info(f"Maximum similarity score: {max_similarity:.3f}")
                
                # Log high similarity results (above 0.7)
                high_similarity = [r for r in query_results if r["similarity_score"] > 0.7]
                logger.info(f"Number of high similarity results (>0.7): {len(high_similarity)}")
            
            logger.info("-" * 80)

def main():
    logger.info("Starting Retrieval Quality Test")
    
    test = RetrievalQualityTest()
    
    # Step 1: Upload and store PDFs
    logger.info("\nStep 1: Uploading and storing PDFs")
    test.upload_and_store_pdfs()
    
    # Step 2: Test queries and get results
    logger.info("\nStep 2: Testing queries")
    results = test.test_queries()
    
    # Step 3: Analyze results
    logger.info("\nStep 3: Analyzing results")
    test.analyze_results(results)
    
    logger.info("\nRetrieval Quality Test completed")

if __name__ == "__main__":
    main()