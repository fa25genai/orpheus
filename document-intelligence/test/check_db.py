"""
Database Content Checker

This script checks and displays what documents, slides, and images are currently 
stored in the Weaviate database. Useful for verifying ingestion results and 
understanding what data is available for retrieval testing.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.startswith('OLLAMA_API_KEY'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"\'')
                break

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from docint_app.vectorstore.weaviate_graph_store import WeaviateGraphStore

class DatabaseChecker:
    """Check and display database contents."""
    
    def __init__(self, base_url: str = "http://localhost:28947"):
        """Initialize the database checker."""
        self.base_url = os.getenv("WEAVIATE_URL", base_url)
        self.store = WeaviateGraphStore(base_url=self.base_url)
        
    def check_connection(self) -> bool:
        """Test if we can connect to the database."""
        try:
            ready = self.store.is_ready()
            if ready:
                logger.info(f"✅ Successfully connected to Weaviate at {self.base_url}")
                return True
            else:
                logger.error(f"❌ Weaviate not ready at {self.base_url}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to Weaviate: {e}")
            return False
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get information about the database schema."""
        try:
            schema = self.store._get("/v1/schema")
            classes = schema.get("classes", [])
            
            schema_info = {
                "total_classes": len(classes),
                "classes": {}
            }
            
            for cls in classes:
                class_name = cls.get("class", "Unknown")
                properties = cls.get("properties", [])
                schema_info["classes"][class_name] = {
                    "description": cls.get("description", ""),
                    "vectorizer": cls.get("vectorizer", ""),
                    "properties": [p.get("name") for p in properties]
                }
            
            return schema_info
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return {}
    
    def get_slide_summary(self) -> Dict[str, Any]:
        """Get summary of slides in the database."""
        try:
            # Query all slides with basic info
            gql = """
            {
              Get {
                Slide {
                  courseId
                  documentId
                  slideNo
                  slideDescription
                  _additional {
                    id
                  }
                }
              }
            }
            """
            
            result = self.store._post("/v1/graphql", {"query": gql})
            slides = result.get("data", {}).get("Get", {}).get("Slide", []) or []
            
            # Organize slides by course and document
            summary = {
                "total_slides": len(slides),
                "courses": {},
                "documents": {}
            }
            
            for slide in slides:
                course_id = slide.get("courseId", "unknown")
                document_id = slide.get("documentId", "unknown")
                slide_no = slide.get("slideNo", 0)
                description = slide.get("slideDescription", "")
                
                # Count by course
                if course_id not in summary["courses"]:
                    summary["courses"][course_id] = {
                        "slide_count": 0,
                        "documents": set(),
                        "slide_range": [float('inf'), 0]
                    }
                
                summary["courses"][course_id]["slide_count"] += 1
                summary["courses"][course_id]["documents"].add(document_id)
                summary["courses"][course_id]["slide_range"][0] = min(
                    summary["courses"][course_id]["slide_range"][0], slide_no
                )
                summary["courses"][course_id]["slide_range"][1] = max(
                    summary["courses"][course_id]["slide_range"][1], slide_no
                )
                
                # Count by document
                if document_id not in summary["documents"]:
                    summary["documents"][document_id] = {
                        "course_id": course_id,
                        "slide_count": 0,
                        "slides": [],
                        "content_preview": ""
                    }
                
                summary["documents"][document_id]["slide_count"] += 1
                summary["documents"][document_id]["slides"].append({
                    "slide_no": slide_no,
                    "preview": description[:100] + "..." if len(description) > 100 else description
                })
                
                # Use first slide's content as document preview
                if slide_no == 1 or not summary["documents"][document_id]["content_preview"]:
                    summary["documents"][document_id]["content_preview"] = description[:200]
            
            # Convert sets to lists for JSON serialization
            for course_data in summary["courses"].values():
                course_data["documents"] = list(course_data["documents"])
                if course_data["slide_range"][0] == float('inf'):
                    course_data["slide_range"] = [0, 0]
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get slide summary: {e}")
            return {"total_slides": 0, "courses": {}, "documents": {}}
    
    def get_image_summary(self) -> Dict[str, Any]:
        """Get summary of images in the database."""
        try:
            # Query all images with basic info
            gql = """
            {
              Get {
                SlideImage {
                  courseId
                  documentId
                  slideNo
                  description
                  _additional {
                    id
                  }
                }
              }
            }
            """
            
            result = self.store._post("/v1/graphql", {"query": gql})
            images = result.get("data", {}).get("Get", {}).get("SlideImage", []) or []
            
            # Organize images by course and document
            summary = {
                "total_images": len(images),
                "courses": {},
                "by_slide": {}
            }
            
            for image in images:
                course_id = image.get("courseId", "unknown")
                document_id = image.get("documentId", "unknown")
                slide_no = image.get("slideNo", 0)
                description = image.get("description", "")
                
                # Count by course
                if course_id not in summary["courses"]:
                    summary["courses"][course_id] = 0
                summary["courses"][course_id] += 1
                
                # Count by slide
                slide_key = f"{document_id}_slide_{slide_no}"
                if slide_key not in summary["by_slide"]:
                    summary["by_slide"][slide_key] = {
                        "course_id": course_id,
                        "document_id": document_id,
                        "slide_no": slide_no,
                        "image_count": 0,
                        "descriptions": []
                    }
                
                summary["by_slide"][slide_key]["image_count"] += 1
                if description:
                    preview = description[:50] + "..." if len(description) > 50 else description
                    summary["by_slide"][slide_key]["descriptions"].append(preview)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get image summary: {e}")
            return {"total_images": 0, "courses": {}, "by_slide": {}}
    
    def display_summary(self):
        """Display a comprehensive summary of database contents."""
        logger.info("=" * 80)
        logger.info("DATABASE CONTENT SUMMARY")
        logger.info("=" * 80)
        
        # Connection check
        if not self.check_connection():
            return
        
        # Schema information
        logger.info("\n📋 SCHEMA INFORMATION")
        logger.info("-" * 40)
        schema_info = self.get_schema_info()
        if schema_info:
            logger.info(f"Total classes: {schema_info.get('total_classes', 0)}")
            for class_name, class_info in schema_info.get("classes", {}).items():
                logger.info(f"  📁 {class_name}")
                logger.info(f"    Description: {class_info.get('description', 'N/A')}")
                logger.info(f"    Properties: {', '.join(class_info.get('properties', []))}")
        
        # Slide information
        logger.info("\n📄 SLIDE INFORMATION")
        logger.info("-" * 40)
        slide_summary = self.get_slide_summary()
        logger.info(f"Total slides: {slide_summary.get('total_slides', 0)}")
        
        if slide_summary.get("courses"):
            logger.info(f"\nCourses ({len(slide_summary['courses'])}):")
            for course_id, course_data in slide_summary["courses"].items():
                slide_range = course_data["slide_range"]
                logger.info(f"  📚 {course_id}")
                logger.info(f"    Slides: {course_data['slide_count']} (range: {slide_range[0]}-{slide_range[1]})")
                logger.info(f"    Documents: {len(course_data['documents'])}")
                for doc in course_data["documents"]:
                    logger.info(f"      📃 {doc}")
        
        if slide_summary.get("documents"):
            logger.info(f"\nDocuments ({len(slide_summary['documents'])}):")
            for doc_id, doc_data in slide_summary["documents"].items():
                logger.info(f"  📃 {doc_id}")
                logger.info(f"    Course: {doc_data['course_id']}")
                logger.info(f"    Slides: {doc_data['slide_count']}")
                slides_info = []
                for slide in sorted(doc_data["slides"], key=lambda x: x["slide_no"])[:5]:  # Show first 5
                    slides_info.append(f"#{slide['slide_no']}")
                if len(doc_data["slides"]) > 5:
                    slides_info.append("...")
                logger.info(f"    Slide numbers: {', '.join(slides_info)}")
                if doc_data["content_preview"]:
                    logger.info(f"    Preview: {doc_data['content_preview'][:150]}...")
        
        # Image information
        logger.info("\n🖼️  IMAGE INFORMATION")
        logger.info("-" * 40)
        image_summary = self.get_image_summary()
        logger.info(f"Total images: {image_summary.get('total_images', 0)}")
        
        if image_summary.get("courses"):
            logger.info(f"\nImages by course:")
            for course_id, count in image_summary["courses"].items():
                logger.info(f"  📚 {course_id}: {count} images")
        
        if image_summary.get("by_slide"):
            slides_with_images = len(image_summary["by_slide"])
            logger.info(f"\nSlides with images: {slides_with_images}")
            
            # Show top slides by image count
            top_slides = sorted(
                image_summary["by_slide"].items(),
                key=lambda x: x[1]["image_count"],
                reverse=True
            )[:10]  # Top 10
            
            if top_slides:
                logger.info("Top slides by image count:")
                for slide_key, slide_data in top_slides:
                    logger.info(f"  📄 {slide_data['document_id']} (Slide {slide_data['slide_no']})")
                    logger.info(f"    Images: {slide_data['image_count']}")
                    if slide_data["descriptions"]:
                        logger.info(f"    Sample: {slide_data['descriptions'][0]}")
        
        # Vector embedding information
        logger.info("\n🔢 VECTOR EMBEDDING INFORMATION")
        logger.info("-" * 40)
        vector_info = self.check_vector_embeddings()
        logger.info(f"Total slides: {vector_info.get('total_slides', 0)}")
        logger.info(f"Slides with vectors: {vector_info.get('slides_with_vectors', 0)}")
        logger.info(f"Slides without vectors: {vector_info.get('slides_without_vectors', 0)}")
        
        if vector_info.get("vector_dimensions"):
            logger.info(f"Vector dimensions: {vector_info['vector_dimensions']}")
        
        if vector_info.get("sample_vectors"):
            logger.info(f"\nSample vector information:")
            for sample in vector_info["sample_vectors"][:3]:  # Show first 3
                logger.info(f"  📄 {sample['slide_id']}")
                logger.info(f"    Dimensions: {sample['vector_dims']}")
                logger.info(f"    Sample values: {[f'{v:.4f}' for v in sample['vector_sample']]}")
                logger.info(f"    Magnitude: {sample['vector_magnitude']:.4f}")
        
        if vector_info.get("slides_missing_vectors"):
            missing_count = len(vector_info["slides_missing_vectors"])
            logger.info(f"\n⚠️  Slides missing vectors ({missing_count}):")
            for missing in vector_info["slides_missing_vectors"][:5]:  # Show first 5
                logger.info(f"  📄 {missing['document_id']} (Slide {missing['slide_no']})")
                logger.info(f"    Content: {missing['content_preview']}...")
        
        # Summary statistics
        logger.info("\n📊 SUMMARY STATISTICS")
        logger.info("-" * 40)
        total_slides = slide_summary.get("total_slides", 0)
        total_images = image_summary.get("total_images", 0)
        total_courses = len(slide_summary.get("courses", {}))
        total_documents = len(slide_summary.get("documents", {}))
        
        logger.info(f"Courses: {total_courses}")
        logger.info(f"Documents: {total_documents}")
        logger.info(f"Slides: {total_slides}")
        logger.info(f"Images: {total_images}")
        
        if total_slides > 0:
            avg_images_per_slide = total_images / total_slides
            logger.info(f"Average images per slide: {avg_images_per_slide:.2f}")
        
        # Vector health check
        slides_with_vectors = vector_info.get("slides_with_vectors", 0)
        if total_slides > 0:
            vector_coverage = (slides_with_vectors / total_slides) * 100
            logger.info(f"Vector coverage: {vector_coverage:.1f}%")
            
            if vector_coverage == 100:
                logger.info("🟢 All slides have vector embeddings")
            elif vector_coverage > 50:
                logger.info("🟡 Most slides have vector embeddings")
            else:
                logger.info("🔴 Many slides missing vector embeddings")
        
        logger.info("\n✅ Database check completed!")
        
    def check_vector_embeddings(self) -> Dict[str, Any]:
        """Check if slides have vector embeddings stored."""
        try:
            # Query slides with vector information
            gql = """
            {
              Get {
                Slide {
                  courseId
                  documentId
                  slideNo
                  slideDescription
                  _additional {
                    id
                    vector
                  }
                }
              }
            }
            """
            
            result = self.store._post("/v1/graphql", {"query": gql})
            slides = result.get("data", {}).get("Get", {}).get("Slide", []) or []
            
            vector_info = {
                "total_slides": len(slides),
                "slides_with_vectors": 0,
                "slides_without_vectors": 0,
                "vector_dimensions": None,
                "sample_vectors": [],
                "slides_missing_vectors": []
            }
            
            for slide in slides:
                additional = slide.get("_additional", {})
                vector = additional.get("vector")
                
                if vector and len(vector) > 0:
                    vector_info["slides_with_vectors"] += 1
                    
                    # Record vector dimensions (should be consistent)
                    if vector_info["vector_dimensions"] is None:
                        vector_info["vector_dimensions"] = len(vector)
                    
                    # Store sample vector info (first 5 slides)
                    if len(vector_info["sample_vectors"]) < 5:
                        vector_info["sample_vectors"].append({
                            "slide_id": f"{slide.get('documentId', 'unknown')}_slide_{slide.get('slideNo', 0)}",
                            "vector_dims": len(vector),
                            "vector_sample": vector[:5],  # First 5 dimensions
                            "vector_magnitude": sum(x*x for x in vector[:10])**0.5  # Magnitude of first 10 dims
                        })
                else:
                    vector_info["slides_without_vectors"] += 1
                    vector_info["slides_missing_vectors"].append({
                        "document_id": slide.get("documentId", "unknown"),
                        "slide_no": slide.get("slideNo", 0),
                        "content_preview": slide.get("slideDescription", "")[:100]
                    })
            
            return vector_info
            
        except Exception as e:
            logger.error(f"Failed to check vector embeddings: {e}")
            return {"total_slides": 0, "slides_with_vectors": 0, "slides_without_vectors": 0}

    def get_course_details(self, course_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific course."""
        try:
            return self.store.get_all_data_for_course(course_id)
        except Exception as e:
            logger.error(f"Failed to get course details for {course_id}: {e}")
            return {}
    
    def export_summary(self, filepath: Optional[str] = None):
        """Export database summary to a JSON file."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(Path(__file__).parent / "logs" / f"db_summary_{timestamp}.json")
        
        # Ensure logs directory exists
        Path(filepath).parent.mkdir(exist_ok=True)
        
        try:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "database_url": self.base_url,
                "schema": self.get_schema_info(),
                "slides": self.get_slide_summary(),
                "images": self.get_image_summary()
            }
            
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📁 Database summary exported to: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to export summary: {e}")

def main():
    """Main function to run the database checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check Weaviate database contents")
    parser.add_argument("--url", default="http://localhost:28947", 
                       help="Weaviate base URL (default: http://localhost:28947)")
    parser.add_argument("--course", help="Get detailed info for a specific course")
    parser.add_argument("--export", help="Export summary to JSON file")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Override URL from environment if set
    base_url = os.getenv("WEAVIATE_URL", args.url)
    
    checker = DatabaseChecker(base_url=base_url)
    
    if args.course:
        logger.info(f"Getting detailed information for course: {args.course}")
        course_details = checker.get_course_details(args.course)
        if course_details:
            print(json.dumps(course_details, indent=2, ensure_ascii=False))
        else:
            logger.warning(f"No data found for course: {args.course}")
    else:
        checker.display_summary()
    
    if args.export:
        checker.export_summary(args.export)
    
if __name__ == "__main__":
    main()
