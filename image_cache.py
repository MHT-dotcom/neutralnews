"""
Enhanced image caching system for NeutralNews.

This module implements a more efficient caching strategy for images by:
1. Maintaining a LRU (Least Recently Used) cache for frequent search terms
2. Prioritizing image generation for popular searches
3. Implementing size-based image optimization
4. Providing metrics for cache performance
"""

import os
import time
import logging
import sqlite3
from PIL import Image
from collections import OrderedDict
from threading import Lock
from flask import current_app
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger('neutralnews.image_cache')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class ImageCache:
    """Efficient image caching system for frequently searched topics."""
    
    def __init__(self, max_size=100, db_path=None, image_dir=None):
        """
        Initialize the image cache.
        
        Args:
            max_size (int): Maximum number of entries in the LRU cache
            db_path (str): Path to SQLite database
            image_dir (str): Directory where images are stored
        """
        self.max_size = max_size
        # Use a hybrid LRU-LFU approach
        # Frequency-based for most popular searches
        # Recency-based for less popular searches
        self.cache = OrderedDict()  # LRU cache
        self.frequency_threshold = 3  # Searches with count >= this are kept based on frequency
        self.cache_lock = Lock()
        self.db_path = db_path
        self.image_dir = image_dir
        self.stats = {
            'hits': 0,
            'misses': 0,
            'failed_generations': 0,
            'successful_generations': 0,
            'webp_conversions': 0,
            'size_optimizations': 0
        }
        
        # Initialize cache from database
        self._initialize_cache()
        
    def _initialize_cache(self):
        """Load most frequently accessed images into the cache from database."""
        if not self.db_path and current_app:
            self.db_path = current_app.config.get("DB_PATH")
        
        if not self.image_dir and current_app:
            self.image_dir = current_app.config.get("IMAGE_DIRECTORY")
            
        if not self.db_path or not self.image_dir:
            logger.warning("Database or image directory not configured")
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Add a searches column if it doesn't exist
            try:
                c.execute("ALTER TABLE search_history ADD COLUMN search_count INTEGER DEFAULT 1")
                logger.info("Added search_count column to search_history")
            except sqlite3.OperationalError:
                logger.debug("search_count column already exists")
                
            # Add columns for image dimensions and format if they don't exist
            try:
                c.execute("ALTER TABLE search_history ADD COLUMN image_width INTEGER DEFAULT NULL")
                c.execute("ALTER TABLE search_history ADD COLUMN image_height INTEGER DEFAULT NULL")
                c.execute("ALTER TABLE search_history ADD COLUMN image_format TEXT DEFAULT NULL")
                c.execute("ALTER TABLE search_history ADD COLUMN image_size_bytes INTEGER DEFAULT NULL")
                logger.info("Added image dimension and format columns to search_history")
            except sqlite3.OperationalError:
                logger.debug("Image dimension and format columns already exist")
                
            # Get most frequently searched queries with images
            c.execute("""
                SELECT query, image_path, search_count FROM search_history 
                WHERE image_path IS NOT NULL
                ORDER BY search_count DESC, timestamp DESC
                LIMIT ?
            """, (self.max_size,))
            
            results = c.fetchall()
            conn.close()
            
            with self.cache_lock:
                for query, image_path, count in results:
                    if image_path and os.path.exists(image_path):
                        # Get image dimensions if available
                        dimensions = None
                        try:
                            if os.path.exists(image_path):
                                with Image.open(image_path) as img:
                                    dimensions = {
                                        'width': img.width,
                                        'height': img.height,
                                        'format': img.format,
                                        'size': os.path.getsize(image_path)
                                    }
                        except Exception as e:
                            logger.warning(f"Couldn't get image dimensions for {image_path}: {str(e)}")
                    
                        self.cache[query] = {
                            'path': image_path,
                            'count': count,
                            'last_accessed': datetime.now(),
                            'dimensions': dimensions,
                            'priority': 'frequency' if count >= self.frequency_threshold else 'recency'
                        }
                    
            logger.info(f"Initialized image cache with {len(self.cache)} entries")
            
        except Exception as e:
            logger.error(f"Error initializing cache: {str(e)}")
            
    def get_image_path(self, query):
        """
        Get the path to the cached image for a query.
        
        Args:
            query (str): The search query
            
        Returns:
            str: Path to the image, or None if not in cache
        """
        with self.cache_lock:
            # Standardize the query
            clean_query = self._clean_query(query)
            
            # Check if in memory cache
            if clean_query in self.cache:
                # Update access time and count
                entry = self.cache.pop(clean_query)
                entry['last_accessed'] = datetime.now()
                # Reinsert at the end (most recently used)
                self.cache[clean_query] = entry
                
                # Track hit
                self.stats['hits'] += 1
                
                # Increment search count in database
                self._increment_search_count(query)
                
                logger.info(f"Cache hit for query: '{query}'")
                return entry['path']
            
            self.stats['misses'] += 1
            logger.info(f"Cache miss for query: '{query}'")
            return None
            
    def add_image(self, query, image_path, dimensions=None, update_db=True):
        """
        Add an image to the cache.
        
        Args:
            query (str): The search query
            image_path (str): Path to the generated image
            dimensions (dict): Image dimensions and format info
            update_db (bool): Whether to update the database with the dimensions
        """
        if not image_path or not os.path.exists(image_path):
            self.stats['failed_generations'] += 1
            logger.warning(f"Cannot add non-existent image to cache: {image_path}")
            return
        
        clean_query = self._clean_query(query)
        
        # Get the image dimensions if not provided
        if not dimensions:
            try:
                with Image.open(image_path) as img:
                    dimensions = {
                        'width': img.width,
                        'height': img.height,
                        'format': img.format.lower() if img.format else os.path.splitext(image_path)[1][1:],
                        'size': os.path.getsize(image_path)
                    }
            except Exception as e:
                logger.warning(f"Couldn't get image dimensions for {image_path}: {str(e)}")
                dimensions = None
        
        with self.cache_lock:
            # Get current search count
            count = self._get_search_count(query) or 1
            
            # Add to cache
            self.cache[clean_query] = {
                'path': image_path,
                'count': count,
                'last_accessed': datetime.now(),
                'dimensions': dimensions,
                'priority': 'frequency' if count >= self.frequency_threshold else 'recency'
            }
            
            # If cache is full, evict least valuable entry
            if len(self.cache) > self.max_size:
                self._evict_cache_entry()
            
            self.stats['successful_generations'] += 1
            
            # Update database with dimensions if requested
            if update_db and dimensions and self.db_path:
                try:
                    conn = sqlite3.connect(self.db_path)
                    c = conn.cursor()
                    c.execute("""
                        UPDATE search_history 
                        SET image_width = ?, image_height = ?, 
                            image_format = ?, image_size_bytes = ?
                        WHERE query = ? AND image_path = ?
                    """, (
                        dimensions.get('width'), 
                        dimensions.get('height'),
                        dimensions.get('format'),
                        dimensions.get('size'),
                        query, image_path
                    ))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error updating image dimensions in database: {str(e)}")
        
        logger.info(f"Added image to cache for query: '{query}'")
        
    def _evict_cache_entry(self):
        """Evict the least valuable entry from the cache based on frequency/recency."""
        # First, try to evict from recency-based entries
        recency_entries = [(k, v) for k, v in self.cache.items() 
                          if v.get('priority') == 'recency']
        
        if recency_entries:
            # Get the oldest accessed recency-based entry
            oldest_key = min(recency_entries, key=lambda x: x[1]['last_accessed'])[0]
            self.cache.pop(oldest_key)
            logger.debug(f"Evicted recency-based entry: {oldest_key}")
            return
        
        # If no recency-based entries, evict the least frequently used
        # Of the frequency-based entries
        frequency_entries = [(k, v) for k, v in self.cache.items() 
                           if v.get('priority') == 'frequency']
        
        if frequency_entries:
            # Get the least frequently used entry
            lfu_key = min(frequency_entries, key=lambda x: x[1]['count'])[0]
            self.cache.pop(lfu_key)
            logger.debug(f"Evicted frequency-based entry: {lfu_key}")
            return
        
        # Fallback to standard LRU behavior
        self.cache.popitem(last=False)
        logger.debug("Evicted oldest entry using standard LRU")
    
    def pregenerate_trending_images(self, trending_topics, generate_callback):
        """
        Pre-generate images for trending topics in the background.
        
        Args:
            trending_topics (list): List of trending topics
            generate_callback (callable): Callback function to generate images
        """
        import threading
        
        def pregeneration_worker(topics):
            logger.info(f"Starting background image pre-generation for {len(topics)} trending topics")
            for headline, keywords in topics:
                clean_query = self._clean_query(headline)
                
                # Skip if already in cache
                if self.get_image_path(clean_query):
                    logger.info(f"Image for '{headline}' already in cache, skipping pre-generation")
                    continue
                
                # Create standard image path
                standard_path = os.path.join(self.image_dir, f"{clean_query}.png")
                
                # Skip if file already exists
                if os.path.exists(standard_path):
                    logger.info(f"Image file for '{headline}' already exists at {standard_path}")
                    self.add_image(clean_query, standard_path)
                    continue
                
                # Generate the image
                try:
                    logger.info(f"Pre-generating image for trending topic: '{headline}'")
                    image_path, status = generate_callback(headline, keywords)
                    if status and image_path:
                        logger.info(f"Successfully pre-generated image for '{headline}'")
                        self.add_image(clean_query, image_path)
                    else:
                        logger.warning(f"Failed to pre-generate image for '{headline}'")
                except Exception as e:
                    logger.error(f"Error pre-generating image for '{headline}': {str(e)}")
        
        # Start background thread for pre-generation
        thread = threading.Thread(target=pregeneration_worker, args=(trending_topics,))
        thread.daemon = True
        thread.start()
    
    def optimize_storage(self, max_age_days=30, target_size_mb=500):
        """
        Optimize storage by removing old/unused images and compressing large ones.
        Also converts PNGs to WebP format for better compression.
        
        Args:
            max_age_days (int): Maximum age for unused images
            target_size_mb (int): Target directory size in MB
        """
        if not self.image_dir:
            logger.warning("Image directory not configured, skipping optimization")
            return
        
        try:
            # Get all image files in the image directory
            image_files = []
            for filename in os.listdir(self.image_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    file_path = os.path.join(self.image_dir, filename)
                    stats = os.stat(file_path)
                    # Get file info
                    image_files.append({
                        'path': file_path,
                        'size': stats.st_size,
                        'last_modified': datetime.fromtimestamp(stats.st_mtime),
                        'filename': filename,
                        'format': os.path.splitext(filename)[1][1:].lower()
                    })
            
            # Sort by last modified time (oldest first)
            image_files.sort(key=lambda x: x['last_modified'])
            
            # Calculate total size
            total_size_bytes = sum(file['size'] for file in image_files)
            total_size_mb = total_size_bytes / (1024 * 1024)
            logger.info(f"Current image directory size: {total_size_mb:.2f} MB ({len(image_files)} files)")
            
            # Remove unused and old images first
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            removed_count = 0
            
            for file_info in image_files:
                # Skip if file is in active cache
                in_cache = False
                for entry in self.cache.values():
                    if file_info['path'] == entry['path']:
                        in_cache = True
                        break
                
                if in_cache:
                    continue
                
                # Check if image is used in database
                filename = file_info['filename']
                image_path = f"/images/{filename}"
                c.execute("SELECT COUNT(*) FROM search_history WHERE image_path = ?", (image_path,))
                count = c.fetchone()[0]
                
                # Remove if:
                # 1. File is older than max_age_days AND not referenced in DB
                # 2. OR if we're over target size and this file isn't frequently used
                cutoff_date = datetime.now() - timedelta(days=max_age_days)
                
                if (file_info['last_modified'] < cutoff_date and count == 0) or \
                   (total_size_mb > target_size_mb and count == 0):
                    try:
                        os.remove(file_info['path'])
                        removed_count += 1
                        total_size_bytes -= file_info['size']
                        total_size_mb = total_size_bytes / (1024 * 1024)
                        logger.info(f"Removed unused image: {file_info['filename']}")
                    except Exception as e:
                        logger.error(f"Failed to remove image {file_info['path']}: {str(e)}")
            
            # Convert PNG files to WebP for better compression
            converted_count = 0
            png_files = [f for f in image_files if f['format'].lower() == 'png' and os.path.exists(f['path'])]
            
            for file_info in png_files:
                try:
                    # Check if the image is still in use (referenced in the database)
                    filename = file_info['filename']
                    image_path = f"/images/{filename}"
                    c.execute("SELECT query FROM search_history WHERE image_path = ?", (image_path,))
                    result = c.fetchone()
                    
                    if not result:
                        continue  # Skip if not in database
                        
                    query = result[0]
                    
                    # Convert PNG to WebP
                    img = Image.open(file_info['path'])
                    webp_path = file_info['path'].replace('.png', '.webp')
                    
                    # Optimize quality based on image size
                    img_size_kb = file_info['size'] / 1024
                    quality = min(90, max(75, int(90 - (img_size_kb / 100))))
                    
                    # Save as WebP
                    img.save(webp_path, 'WEBP', quality=quality)
                    
                    # Check if the WebP file is actually smaller
                    webp_size = os.path.getsize(webp_path)
                    if webp_size < file_info['size']:
                        # Update reference in database
                        webp_filename = os.path.basename(webp_path)
                        new_image_path = f"/images/{webp_filename}"
                        c.execute("UPDATE search_history SET image_path = ? WHERE image_path = ?", 
                                  (new_image_path, image_path))
                        
                        # Remove the original PNG
                        os.remove(file_info['path'])
                        
                        # Update cache if needed
                        with self.cache_lock:
                            clean_query = self._clean_query(query)
                            if clean_query in self.cache and self.cache[clean_query]['path'] == file_info['path']:
                                self.cache[clean_query]['path'] = webp_path
                        
                        converted_count += 1
                        savings = file_info['size'] - webp_size
                        total_size_bytes -= savings
                        total_size_mb = total_size_bytes / (1024 * 1024)
                        logger.info(f"Converted {filename} to WebP - saved {savings/1024:.1f} KB")
                        self.stats['webp_conversions'] += 1
                    else:
                        # WebP is not smaller, keep the PNG and delete the WebP
                        os.remove(webp_path)
                except Exception as e:
                    logger.error(f"Failed to convert {file_info['path']} to WebP: {str(e)}")
            
            # Create responsive sizes for large images that are frequently used
            c.execute("""
                SELECT query, image_path, search_count, image_width, image_height, image_format, image_size_bytes
                FROM search_history 
                WHERE image_path IS NOT NULL AND search_count > 2
                ORDER BY search_count DESC
                LIMIT 20
            """)
            
            popular_images = c.fetchall()
            responsive_count = 0
            
            for query, image_path, count, width, height, img_format, size in popular_images:
                if not image_path or not image_path.startswith('/images/'):
                    continue
                    
                # Map to filesystem path
                file_path = os.path.join(self.image_dir, os.path.basename(image_path))
                
                if not os.path.exists(file_path):
                    continue
                    
                # Only create responsive sizes for large images
                try:
                    if not width or not height:
                        # Get dimensions if not stored
                        with Image.open(file_path) as img:
                            width, height = img.size
                            
                    # Skip if image is already small
                    if width <= 800 and height <= 800:
                        continue
                        
                    # Create responsive sizes
                    with Image.open(file_path) as img:
                        filename_base, ext = os.path.splitext(file_path)
                        
                        # Medium size (800px)
                        if width > 800 or height > 800:
                            med_path = f"{filename_base}_800{ext}"
                            if not os.path.exists(med_path):
                                med_img = img.copy()
                                med_img.thumbnail((800, 800), Image.LANCZOS)
                                med_img.save(med_path, quality=85, optimize=True)
                                logger.info(f"Created medium responsive image: {os.path.basename(med_path)}")
                                responsive_count += 1
                        
                        # Small size (400px)
                        if width > 400 or height > 400:
                            small_path = f"{filename_base}_400{ext}"
                            if not os.path.exists(small_path):
                                small_img = img.copy()
                                small_img.thumbnail((400, 400), Image.LANCZOS)
                                small_img.save(small_path, quality=80, optimize=True)
                                logger.info(f"Created small responsive image: {os.path.basename(small_path)}")
                                responsive_count += 1
                except Exception as e:
                    logger.error(f"Failed to create responsive sizes for {file_path}: {str(e)}")
                
            conn.commit()
            conn.close()
            
            # If still over target size, compress remaining large images
            remaining_size_mb = sum(os.path.getsize(f) for f in os.listdir(self.image_dir) if os.path.isfile(os.path.join(self.image_dir, f))) / (1024 * 1024)
            
            if remaining_size_mb > target_size_mb:
                compressed_count = 0
                # Sort remaining files by size (largest first)
                remaining_files = []
                for filename in os.listdir(self.image_dir):
                    if not filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        continue
                        
                    file_path = os.path.join(self.image_dir, filename)
                    if not os.path.exists(file_path):
                        continue
                        
                    remaining_files.append({
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'filename': filename
                    })
                    
                remaining_files.sort(key=lambda x: x['size'], reverse=True)
                
                for file_info in remaining_files:
                    # If we're under target size, stop compressing
                    if remaining_size_mb <= target_size_mb:
                        break
                    
                    try:
                        # Skip small files
                        if file_info['size'] < 100 * 1024:  # Skip files under 100 KB
                            continue
                            
                        # Compress image
                        img = Image.open(file_info['path'])
                        original_size = file_info['size']
                        
                        # If image is WebP, optimize based on size
                        if file_info['path'].endswith('.webp'):
                            img_size_mb = original_size / (1024 * 1024)
                            quality = min(85, max(60, int(85 - (img_size_mb * 10))))
                            img.save(file_info['path'], format='WEBP', quality=quality)
                        else:
                            # For other formats, use format-specific optimization
                            format_name = os.path.splitext(file_info['path'])[1][1:].upper()
                            img_size_mb = original_size / (1024 * 1024)
                            quality = min(90, max(65, int(90 - (img_size_mb * 10))))
                            
                            if format_name == 'PNG':
                                img.save(file_info['path'], format='PNG', optimize=True, quality=quality)
                            elif format_name in ('JPG', 'JPEG'):
                                img.save(file_info['path'], format='JPEG', optimize=True, quality=quality)
                            else:
                                # Skip unsupported formats
                                continue
                        
                        # Update size info
                        new_size = os.path.getsize(file_info['path'])
                        savings = original_size - new_size
                        
                        if savings > 0:
                            compressed_count += 1
                            self.stats['size_optimizations'] += 1
                            remaining_size_mb -= savings / (1024 * 1024)
                            logger.info(f"Compressed {file_info['filename']} - saved {savings/1024:.1f} KB")
                    except Exception as e:
                        logger.error(f"Failed to compress {file_info['path']}: {str(e)}")
            
            logger.info(f"Storage optimization completed: removed {removed_count} images, "
                       f"converted {converted_count} to WebP, "
                       f"created {responsive_count} responsive versions, "
                       f"compressed {compressed_count} images, "
                       f"final size: {remaining_size_mb:.2f} MB")
            
        except Exception as e:
            logger.error(f"Error during storage optimization: {str(e)}", exc_info=True)
    
    def get_stats(self):
        """Get cache statistics."""
        with self.cache_lock:
            stats = self.stats.copy()
            stats['cache_size'] = len(self.cache)
            stats['cache_max_size'] = self.max_size
            
            # Calculate hit rate
            total_requests = stats['hits'] + stats['misses']
            stats['hit_rate'] = stats['hits'] / total_requests if total_requests > 0 else 0
            
            return stats
    
    def _clean_query(self, query):
        """Standardize query format for cache keys."""
        return "".join(c if c.isalnum() else "-" for c in query.lower())
    
    def _increment_search_count(self, query):
        """Update search count for a query in the database."""
        if not self.db_path:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                UPDATE search_history 
                SET search_count = search_count + 1
                WHERE query = ?
            """, (query,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating search count: {str(e)}")
    
    def _get_search_count(self, query):
        """Get the current search count for a query."""
        if not self.db_path:
            return 1
            
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT search_count FROM search_history WHERE query = ?", (query,))
            result = c.fetchone()
            conn.close()
            
            return result[0] if result else 1
        except Exception as e:
            logger.error(f"Error getting search count: {str(e)}")
            return 1

# Singleton instance
_instance = None

def get_instance(max_size=100, db_path=None, image_dir=None):
    """Get the singleton instance of ImageCache."""
    global _instance
    if _instance is None:
        _instance = ImageCache(max_size, db_path, image_dir)
    return _instance 