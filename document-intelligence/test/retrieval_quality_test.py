import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import asyncio
import json

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
        self.test_start_time = datetime.now()
        self.uploaded_documents = []
        self.test_results = {
            "test_metadata": {
                "start_time": self.test_start_time.isoformat(),
                "test_version": "1.0",
                "description": "Retrieval Quality Test for Document Intelligence System"
            },
            "uploaded_pdfs": [],
            "query_results": [],
            "analysis": {}
        }

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
            
            # Track uploaded document
            self.test_results["uploaded_pdfs"].append({
                "filename": pdf_file.name,
                "course_id": course_id,
                "document_id": document_id,
                "file_size_bytes": len(pdf_data),
                "upload_time": datetime.now().isoformat()
            })
            
            logger.info(f"Successfully uploaded and ingested {pdf_file.name} with document_id: {document_id}")
            logger.info(f"Completed processing {pdf_file.name}")

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
            
            # Store query result metadata
            query_result = {
                "query": query,
                "topic": query_info["topic"],
                "expected_relevant": query_info["expected_relevant"],
                "total_hits": response['total_hits'],
                "num_slides": len(response['slides']),
                "num_content_items": len(response['content']),
                "search_time": datetime.now().isoformat(),
                "errors": response['errors'],
                "results": []
            }
            
            for i, content in enumerate(response['content']):
                logger.info(f"\nResult {i+1}:")
                logger.info(f"Content: {content[:200]}...")  # Show first 200 chars
                
                result_item = {
                    "content": content,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "slide_info": response['slides'][i] if i < len(response['slides']) else None
                }
                
                query_result["results"].append(result_item)
                
                results.append({
                    "query": query,
                    "topic": query_info["topic"],
                    "expected_relevant": query_info["expected_relevant"],
                    "content": content,
                    "slide_info": response['slides'][i] if i < len(response['slides']) else None
                })
            
            self.test_results["query_results"].append(query_result)
            
            if response['errors']:
                logger.warning(f"Errors in search: {response['errors']}")
            
            logger.info("-" * 80)

        return results

    def analyze_results(self, results):
        """Analyze the quality of retrieval results."""
        logger.info("\nRESULTS ANALYSIS")
        logger.info("=" * 80)
        
        analysis_summary = {
            "total_queries": len(set(r["query"] for r in results)),
            "total_results": len(results),
            "queries_analysis": []
        }
        
        # Aggregate metrics by query
        for query_info in set((r["query"], r["topic"]) for r in results):
            query_results = [r for r in results if r["query"] == query_info[0]]
            
            logger.info(f"\nQuery: {query_info[0]}")
            logger.info(f"Topic: {query_info[1]}")
            logger.info(f"Number of results: {len(query_results)}")
            
            query_analysis = {
                "query": query_info[0],
                "topic": query_info[1],
                "num_results": len(query_results),
                "expected_relevant": query_results[0]["expected_relevant"] if query_results else None
            }
            
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
                    
                    query_analysis.update({
                        "has_scores": True,
                        "avg_score": avg_score,
                        "max_score": max_score,
                        "high_score_count": len(high_score)
                    })
                else:
                    logger.info("No score information available in results")
                    query_analysis["has_scores"] = False
            
            analysis_summary["queries_analysis"].append(query_analysis)
            logger.info("-" * 80)
        
        # Store analysis in test results
        self.test_results["analysis"] = analysis_summary

    def save_log_file(self):
        """Save test results to a log file."""
        # Complete test metadata
        self.test_results["test_metadata"]["end_time"] = datetime.now().isoformat()
        self.test_results["test_metadata"]["duration_seconds"] = (
            datetime.now() - self.test_start_time
        ).total_seconds()
        
        # Create logs directory if it doesn't exist
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Generate log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"retrieval_quality_test_{timestamp}.json"
        log_path = log_dir / log_filename
        
        # Save detailed results as JSON
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        # Also create a human-readable summary
        summary_filename = f"retrieval_quality_test_summary_{timestamp}.txt"
        summary_path = log_dir / summary_filename
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("RETRIEVAL QUALITY TEST SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Test Start Time: {self.test_results['test_metadata']['start_time']}\n")
            f.write(f"Test End Time: {self.test_results['test_metadata']['end_time']}\n")
            f.write(f"Duration: {self.test_results['test_metadata']['duration_seconds']:.2f} seconds\n\n")
            
            f.write("UPLOADED PDFs:\n")
            f.write("-" * 20 + "\n")
            for pdf in self.test_results["uploaded_pdfs"]:
                f.write(f"- {pdf['filename']} (Course: {pdf['course_id']}, Size: {pdf['file_size_bytes']} bytes)\n")
            f.write("\n")
            
            f.write("QUERY RESULTS:\n")
            f.write("-" * 20 + "\n")
            for query_result in self.test_results["query_results"]:
                f.write(f"Query: {query_result['query']}\n")
                f.write(f"Topic: {query_result['topic']}\n")
                f.write(f"Expected Relevant: {query_result['expected_relevant']}\n")
                f.write(f"Total Hits: {query_result['total_hits']}\n")
                f.write(f"Content Items: {query_result['num_content_items']}\n")
                if query_result['errors']:
                    f.write(f"Errors: {query_result['errors']}\n")
                f.write("\n")
            
            f.write("ANALYSIS SUMMARY:\n")
            f.write("-" * 20 + "\n")
            analysis = self.test_results["analysis"]
            f.write(f"Total Queries: {analysis['total_queries']}\n")
            f.write(f"Total Results: {analysis['total_results']}\n")
            
            for query_analysis in analysis["queries_analysis"]:
                f.write(f"\n{query_analysis['topic']}:\n")
                f.write(f"  Results: {query_analysis['num_results']}\n")
                f.write(f"  Expected Relevant: {query_analysis['expected_relevant']}\n")
                if query_analysis.get("has_scores"):
                    f.write(f"  Avg Score: {query_analysis['avg_score']:.3f}\n")
                    f.write(f"  Max Score: {query_analysis['max_score']:.3f}\n")
                    f.write(f"  High Score Results: {query_analysis['high_score_count']}\n")
        
        logger.info(f"\nLog files saved:")
        logger.info(f"  Detailed results: {log_path}")
        logger.info(f"  Summary: {summary_path}")
        
        return log_path, summary_path

async def main():
    logger.info("Starting Retrieval Quality Test")
    
    test = RetrievalQualityTest()
    
    # Step 1: Upload and ingest PDFs
    logger.info("\nStep 1: Uploading and ingesting PDFs")
    await test.upload_and_store_pdfs()
    
    # Step 2: Test queries and get results
    logger.info("\nStep 2: Testing queries")
    results = await test.test_queries()
    
    # Step 3: Analyze results
    logger.info("\nStep 3: Analyzing results")
    test.analyze_results(results)
    
    # Step 4: Save log files
    logger.info("\nStep 4: Saving log files")
    log_path, summary_path = test.save_log_file()
    
    logger.info("\nRetrieval Quality Test completed")
    logger.info(f"Check the log files for detailed results:")
    logger.info(f"  {log_path}")
    logger.info(f"  {summary_path}")

if __name__ == "__main__":
    asyncio.run(main())