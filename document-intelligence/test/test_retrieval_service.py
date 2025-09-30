"""
Simple Retrieval Service Test

Tests basic query functionality and shows:
1. Query results (slides and images found)  
2. Similarity scores for each result
3. Simple pass/fail status

No complex analysis - just basic retrieval testing.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up environment variables if not already set
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    logger.info(f"Loading environment from {env_file}")
    with open(env_file) as f:
        for line in f:
            if line.startswith('OLLAMA_API_KEY'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"\'')
                logger.info(f"Loaded {key}: {value[:20]}...")
                break
else:
    logger.warning("OLLAMA_API_KEY not found. Please set it in environment or .env file")

# Verify API key is loaded
if not os.getenv('OLLAMA_API_KEY'):
    logger.error("❌ OLLAMA_API_KEY still not set after loading .env file")
    os.environ['OLLAMA_API_KEY'] = 'your-ollama-api-key-here'
else:
    api_key = os.getenv('OLLAMA_API_KEY')
    if api_key:
        logger.info(f"✅ OLLAMA_API_KEY loaded: {api_key[:20]}...")
    else:
        logger.error("❌ OLLAMA_API_KEY is None")

# Add the src directory to the path
import sys
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from docint_app.services.retrieval_service import RetrievalService

class SimpleRetrievalTest:
    def __init__(self, base_url: str = "http://localhost:28947"):
        """Initialize the simple retrieval test."""
        self.base_url = base_url
        self.retrieval_service = None
        self.test_results = {
            "test_timestamp": datetime.now().isoformat(),
            "base_url": base_url,
            "queries": [],
            "summary": {}
        }
        
    async def initialize(self):
        """Initialize the retrieval service."""
        try:
            logger.info(f"Initializing RetrievalService with base_url: {self.base_url}")
            self.retrieval_service = RetrievalService(base_url=self.base_url)
            
            # Test connection
            health = self.retrieval_service.check_health()
            logger.info(f"Service health: {health}")
            
            if health.get("status") != "healthy":
                raise Exception(f"Service not healthy: {health}")
                
        except Exception as e:
            logger.error(f"Failed to initialize retrieval service: {e}")
            raise

    async def test_query(self, query: str, description: str, k: int = 5):
        """Test a single query and show basic results."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {description}")
        logger.info(f"Query: '{query}'")
        logger.info(f"{'='*60}")
        
        try:
            # Ensure service is initialized
            if self.retrieval_service is None:
                raise Exception("Retrieval service not initialized")
                
            # Perform the search
            results = await self.retrieval_service.search(
                query=query,
                course_id=None,
                k=k,
                alpha=0.8,  # 80% text, 20% image
                include_images=True
            )
            
            # Show results
            total_hits = results.get("total_hits", 0)
            slides = results.get("slides", [])
            images = results.get("images", [])
            
            logger.info(f"\nResults Summary:")
            logger.info(f"  Total hits: {total_hits}")
            logger.info(f"  Slides found: {len(slides)}")
            logger.info(f"  Images found: {len(images)}")
            
            if slides:
                logger.info(f"\nSlide Results:")
                for i, slide in enumerate(slides, 1):
                    scores = slide.get("scores", {})
                    fused_score = scores.get("fused", 0)
                    text_sim = scores.get("text_similarity", 0)
                    image_sim = scores.get("image_similarity", 0)
                    
                    logger.info(f"  {i}. Document: {slide.get('document_id', 'N/A')}")
                    logger.info(f"     Slide: {slide.get('slide_no', 'N/A')}")
                    logger.info(f"     Course: {slide.get('course_id', 'N/A')}")
                    logger.info(f"     Similarity Score: {fused_score:.4f}")
                    logger.info(f"     Text Similarity: {text_sim:.4f}")
                    logger.info(f"     Image Similarity: {image_sim:.4f}")
                    
                    # Show content preview
                    content = slide.get("description", "")
                    if content:
                        preview = content[:150] + "..." if len(content) > 150 else content
                        logger.info(f"     Content: {preview}")
                    logger.info("")
                
                # Show overall similarity score
                top_score = slides[0].get("scores", {}).get("fused", 0) if slides else 0
                logger.info(f"Top similarity score: {top_score:.4f}")
                
                if top_score > 0.75:
                    logger.info("✅ HIGH relevance - good semantic match")
                elif top_score > 0.5:
                    logger.info("🟡 MODERATE relevance - some semantic similarity")
                else:
                    logger.info("❌ LOW relevance - minimal semantic similarity")
            else:
                logger.info("❌ No results found")
                
            result = {
                "query": query,
                "description": description,
                "status": "success",
                "total_hits": total_hits,
                "slides_found": len(slides),
                "images_found": len(images),
                "top_similarity_score": slides[0].get("scores", {}).get("fused", 0) if slides else 0,
                "slides_details": []
            }
            
            # Add slide details for JSON export
            for slide in slides:
                slide_detail = {
                    "document_id": slide.get("document_id", "N/A"),
                    "slide_no": slide.get("slide_no", "N/A"),
                    "course_id": slide.get("course_id", "N/A"),
                    "scores": slide.get("scores", {}),
                    "content_preview": slide.get("description", "")[:150] + "..." if len(slide.get("description", "")) > 150 else slide.get("description", "")
                }
                result["slides_details"].append(slide_detail)
            
            return result
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            result = {
                "query": query,
                "description": description,
                "status": "failed",
                "error": str(e),
                "total_hits": 0,
                "slides_found": 0,
                "images_found": 0,
                "top_similarity_score": 0,
                "slides_details": []
            }
            return result

    async def run_all_tests(self):
        """Run all retrieval tests."""
        logger.info("Starting Simple Retrieval Service Tests")
        logger.info(f"Testing against database at: {self.base_url}")
        
        # Initialize service
        await self.initialize()
        
        # Define test queries
        test_queries = [
            # === IRRELEVANT QUERIES (should return 0 results) ===
            {
                "query": "photosynthesis in plant cells and chloroplast function",
                "description": "Biology query (should return no relevant results)"
            },
            {
                "query": "neural networks and deep learning algorithms machine learning",
                "description": "AI/ML query (should return no relevant results)"
            },
            {
                "query": "quantum computing qubits superposition entanglement",
                "description": "Quantum computing query (should return no relevant results)"
            },
            
            # === RELEVANT QUERIES (should return high-scoring results) ===
            {
                "query": "What is a method signature in java",
                "description": "should match W01U04 content"
            },
            {
                "query": "What are basic data types in Java",
                "description": "Basic types query (should match W01U03 content)"  
            },
            {
                "query": "What is public static void main in Java",
                "description": "Methods query (should match W01U04 content)"
            },
            {
                "query": "UML class diagrams unified modeling language software design",
                "description": "UML query (should match W01U05 content)"
            },
            {
                "query": "What is an expression in java",
                "description": "Expressions query (should match W02U01 content)"
            },
            {
                "query": "programming languages compiled interpreted Java",
                "description": "Course-specific programming query (should match W10 content)"
            },
            {
                "query": "Stephan Krusche Introduction to Programming W10",
                "description": "Instructor and course-specific query (should match W10 content)"
            },
            
            # === SOMEWHAT SIMILAR QUERIES (related concepts but not exact matches) ===
            {
                "query": "for loops and while loops in programming iteration control structures",
                "description": "Control structures query (similar to programming but not covered in these slides)"
            },
            {
                "query": "arrays lists data structures memory allocation",
                "description": "Data structures query (programming-related but not specifically covered)"
            },
            {
                "query": "exception handling try catch finally error management",
                "description": "Exception handling query (advanced topic not in basic slides)"
            },
            {
                "query": "software testing unit testing debugging code quality",
                "description": "Testing concepts query (software engineering but not in these slides)"
            }
        ]
        
        # Run each test
        all_results = []
        for i, test_config in enumerate(test_queries, 1):
            logger.info(f"\n" + "="*80)
            logger.info(f"TEST {i}/{len(test_queries)}")
            logger.info(f"="*80)
            
            result = await self.test_query(
                query=test_config["query"],
                description=test_config["description"],
                k=5
            )
            
            all_results.append(result)
            self.test_results["queries"].append(result)
        
        # Generate simple summary
        logger.info(f"\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info(f"="*80)
        
        successful_tests = sum(1 for r in all_results if r.get("status") == "success")
        tests_with_results = sum(1 for r in all_results if r.get("slides_found", 0) > 0)
        
        logger.info(f"Total Tests: {len(all_results)}")
        logger.info(f"Successful Tests: {successful_tests}")
        logger.info(f"Tests with Results: {tests_with_results}")
        
        logger.info(f"\nDetailed Results:")
        for result in all_results:
            status = "✅" if result.get("status") == "success" else "❌"
            slides_found = result.get("slides_found", 0)
            top_score = result.get("top_similarity_score", 0)
            
            logger.info(f"  {status} {result.get('description', 'N/A')}")
            logger.info(f"      Query: '{result.get('query', 'N/A')}'")
            logger.info(f"      Results: {slides_found} slides, Top score: {top_score:.4f}")
        
        # Store summary in test results
        self.test_results["summary"] = {
            "total_tests": len(all_results),
            "successful_tests": successful_tests,
            "tests_with_results": tests_with_results,
            "success_rate": successful_tests / len(all_results) * 100 if all_results else 0,
            "results_rate": tests_with_results / len(all_results) * 100 if all_results else 0
        }
        
        # Save results to JSON file
        self._save_results_to_json()
        
        logger.info(f"\n🎉 Simple retrieval tests completed!")
        return all_results
    
    def _save_results_to_json(self):
        """Save test results to a JSON file."""
        # Create logs directory if it doesn't exist
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simple_retrieval_test_{timestamp}.json"
        filepath = logs_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📄 Test results saved to: {filepath}")
async def main():
    """Main test function."""
    # Override base URL if provided via environment
    base_url = os.getenv("WEAVIATE_URL", "http://localhost:28947")
    
    tester = SimpleRetrievalTest(base_url=base_url)
    
    try:
        results = await tester.run_all_tests()
        logger.info("\n🎉 Retrieval quality tests completed successfully!")
        return results
    except Exception as e:
        logger.error(f"❌ Tests failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
