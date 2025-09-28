import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import asyncio

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
        # Use localhost for local testing instead of docker hostname
        base_url = "http://localhost:28947"
        self.pdf_upload_service = PDFUploadService(base_url=base_url)
        self.ingestion_service = IngestionService(base_url=base_url)
        self.retrieval_service = RetrievalService(base_url=base_url)
        self.graph_store = WeaviateGraphStore(base_url=base_url)

    async def upload_and_store_pdfs(self):
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
            
            document_id = await self.pdf_upload_service.upload_pdf(
                course_id=course_id,
                body=pdf_data
            )
            
            logger.info(f"Successfully processed {pdf_file.name} with document_id: {document_id}")

    async def test_queries(self):
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
            
            # Get results from retrieval service using the search method
            response = await self.retrieval_service.search(query, k=5)
            
            # Log results
            logger.info(f"Number of results: {response['total_hits']}")
            logger.info(f"Number of slides returned: {len(response['slides'])}")
            logger.info(f"Number of content items: {len(response['content'])}")
            
            for i, content in enumerate(response['content']):
                logger.info(f"\nResult {i+1}:")
                logger.info(f"Content: {content[:200]}...")  # Show first 200 chars
                
                results.append({
                    "query": query,
                    "topic": query_info["topic"],
                    "expected_relevant": query_info["expected_relevant"],
                    "content": content,
                    "slide_info": response['slides'][i] if i < len(response['slides']) else None
                })
            
            if response['errors']:
                logger.warning(f"Errors in search: {response['errors']}")
            
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
                # Check if slide_info has score information
                has_scores = any(r.get("slide_info") and isinstance(r["slide_info"], dict) and "score" in r["slide_info"] for r in query_results)
                
                if has_scores:
                    scores = [r["slide_info"]["score"] for r in query_results if r.get("slide_info") and "score" in r["slide_info"]]
                    avg_score = sum(scores) / len(scores)
                    max_score = max(scores)
                    
                    logger.info(f"Average score: {avg_score:.3f}")
                    logger.info(f"Maximum score: {max_score:.3f}")
                    
                    # Log high score results (above 0.7)
                    high_score = [r for r in query_results if r.get("slide_info") and r["slide_info"].get("score", 0) > 0.7]
                    logger.info(f"Number of high score results (>0.7): {len(high_score)}")
                else:
                    logger.info("No score information available in results")
            
            logger.info("-" * 80)

async def main():
    logger.info("Starting Retrieval Quality Test")
    
    test = RetrievalQualityTest()
    
    # Step 1: Upload and store PDFs
    logger.info("\nStep 1: Uploading and storing PDFs")
    await test.upload_and_store_pdfs()
    
    # Step 2: Test queries and get results
    logger.info("\nStep 2: Testing queries")
    results = await test.test_queries()
    
    # Step 3: Analyze results
    logger.info("\nStep 3: Analyzing results")
    test.analyze_results(results)
    
    logger.info("\nRetrieval Quality Test completed")

if __name__ == "__main__":
    asyncio.run(main())