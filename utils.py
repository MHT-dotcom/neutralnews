from werkzeug.utils import secure_filename

def get_image_filename(headline):
    """
    Convert a headline into the corresponding image filename.
    Usage: print this when adding new topics to know what to name your image files.
    """
    return secure_filename(headline.lower())

# Example usage in a debug route
@app.route('/debug/filenames')
def debug_filenames():
    topics = get_trending_topics(datetime.now().strftime("%Y-%m-%d"))
    filename_guide = ""
    for topic in topics:
        headline = topic[0]
        filename = get_image_filename(headline)
        filename_guide += f"Headline: {headline}\nFilename: {filename}.jpg\n\n"
    return f"<pre>{filename_guide}</pre>" 