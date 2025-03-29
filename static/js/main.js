console.log('main.js loaded');

$(document).ready(function() {
    console.log('jQuery ready');
    
    // Verify form exists
    console.log('Search form exists:', $('#search-form').length > 0);
    
    // Log the number of trending cards found
    const cardCount = $('.trending-card').length;
    console.log(`Found ${cardCount} trending-card elements`);

    // Log styles and positions for each card to debug click and hover issues
    $('.trending-card').each(function(index) {
        const $card = $(this);
        const cardText = $card.find('h3').text().trim();
        const computedStyle = window.getComputedStyle($card[0]);
        const rect = $card[0].getBoundingClientRect();
        console.log(`Card ${index + 1} (${cardText}):`, {
            pointerEvents: computedStyle.pointerEvents,
            zIndex: computedStyle.zIndex,
            position: computedStyle.position,
            display: computedStyle.display,
            visibility: computedStyle.visibility,
            boundingBox: {
                top: rect.top,
                left: rect.left,
                width: rect.width,
                height: rect.height
            }
        });
    });
    
    var $loading = $('.loading');
    var $results = $('#results');
    var $errorMessage = $results.find('.error-message');
    var $pullIndicator = $('.pull-indicator');
    var $trendingContainer = $('.trending-container');
    var $imageContainer = $('#image-container'); // Ensure this exists in HTML
    var startY = 0;
    var pullThreshold = 80;
    var isPulling = false;
    
    // Handle search form submission (hide trending container)
    $('#search-form').on('submit', function(e) {
        e.preventDefault();
        const query = $(this).find('input[name="event"]').val();
        Analytics.trackSearch(query);
        $trendingContainer.hide();
    });
    
    // Pull to refresh functionality for mobile
    document.addEventListener('touchstart', function(e) {
        startY = e.touches[0].clientY;
        if (window.scrollY <= 0) {
            isPulling = true;
        }
    }, { passive: true });
    
    document.addEventListener('touchmove', function(e) {
        if (!isPulling) return;
        var currentY = e.touches[0].clientY;
        var pullDistance = currentY - startY;
        if (pullDistance > 0 && pullDistance < pullThreshold) {
            $pullIndicator.addClass('active');
            e.preventDefault();
        }
    }, { passive: false });
    
    document.addEventListener('touchend', function(e) {
        if (!isPulling) return;
        var currentY = e.changedTouches[0].clientY;
        var pullDistance = currentY - startY;
        if (pullDistance > pullThreshold) {
            window.location.reload();
        } else {
            $pullIndicator.removeClass('active');
        }
        isPulling = false;
    }, { passive: true });
    
    // Add active state for buttons on mobile
    $('.search-button, .clear-button').on('touchstart', function() {
        $(this).css('opacity', '0.8');
    }).on('touchend touchcancel', function() {
        $(this).css('opacity', '1');
    });
    
    // Sentiment color utility
    function getSentimentColor(score) {
        if (score === 0) return '#e2e8f0';  // Neutral gray
        let red, green, blue;
        if (score < 0) {
            let factor = 1 + score;  // Convert -1..0 to 0..1
            red = 239;  // #ef4444
            green = Math.round(68 + (148 * factor));
            blue = Math.round(68 + (148 * factor));
        } else {
            let factor = score;  // Already 0..1
            red = Math.round(226 - (127 * factor));
            green = Math.round(232 - (111 * factor));
            blue = Math.round(240 + (15 * factor));
        }
        return `rgb(${red}, ${green}, ${blue})`;
    }
    
    // Sentiment width utility
    function getSentimentWidth(score) {
        return 20 + (Math.abs(score) * 80) + '%';
    }
    
    // Sentiment label utility
    function getSentimentLabel(score) {
        if (Math.abs(score) < 0.2) return "Neutral";
        if (score < -0.6) return "Very Negative";
        if (score < -0.2) return "Somewhat Negative";
        if (score > 0.6) return "Very Positive";
        if (score > 0.2) return "Somewhat Positive";
        return "Neutral";
    }
    
    // Source color utility
    function getSourceColor(sourceName, index) {
        const sourceColors = {
            'BBC News': '#BB1919', 'CNN': '#CC0000', 'Fox News': '#003366',
            'The Guardian': '#052962', 'The New York Times': '#000000',
            'Reuters': '#FF8000', 'Associated Press': '#FF0000',
            'Washington Post': '#000000', 'CNBC': '#005594', 'Bloomberg': '#000000'
        };
        return sourceColors[sourceName] || `hsl(${(index * 137.5) % 360}, 70%, 50%)`;
    }
    
    // Calculate balance score
    function calculateBalanceScore(sourceDistribution) {
        if (!sourceDistribution || Object.keys(sourceDistribution).length === 0) return 0;
        const sourceCount = Object.keys(sourceDistribution).length;
        const totalArticles = Object.values(sourceDistribution).reduce((sum, count) => sum + count, 0);
        const idealPercentage = 1 / sourceCount;
        let totalDeviation = 0;
        for (const source in sourceDistribution) {
            const actualPercentage = sourceDistribution[source] / totalArticles;
            totalDeviation += Math.abs(actualPercentage - idealPercentage);
        }
        const maxDeviation = 2 - (2 / sourceCount);
        return Math.round(100 * (1 - (totalDeviation / maxDeviation)));
    }
    
    // Create source distribution visualization
    function createSourceDistribution(sourceDistribution) {
        if (!sourceDistribution || Object.keys(sourceDistribution).length === 0) return;
        const $sourceChart = $('#source-chart');
        const $sourceLegend = $('#source-legend');
        $sourceChart.empty();
        $sourceLegend.empty();
        
        const sources = Object.keys(sourceDistribution);
        const totalArticles = Object.values(sourceDistribution).reduce((sum, count) => sum + count, 0);
        
        $('#source-count').text(sources.length);
        const balanceScore = calculateBalanceScore(sourceDistribution);
        $('#balance-score').text(balanceScore + '/100');
        
        sources.forEach((source, index) => {
            const count = sourceDistribution[source];
            const percentage = Math.round((count / totalArticles) * 100);
            const height = Math.max(20, percentage * 2);
            const color = getSourceColor(source, index);
            
            const $bar = $('<div>')
                .addClass('source-bar tooltip')
                .css({ 'height': height + 'px', 'background-color': color })
                .appendTo($sourceChart);
            $('<div>').addClass('source-percentage').text(percentage + '%').appendTo($bar);
            $('<span>').addClass('tooltip-text').text(`${source}: ${count} articles (${percentage}%)`).appendTo($bar);
            
            const $legendItem = $('<div>').addClass('legend-item').appendTo($sourceLegend);
            $('<div>').addClass('legend-color').css('background-color', color).appendTo($legendItem);
            $('<div>').addClass('legend-label').text(`${source} (${count})`).appendTo($legendItem);
        });
        
        if (window.innerWidth <= 640 && sources.length > 6) {
            const $legendItems = $sourceLegend.find('.legend-item');
            $legendItems.slice(6).hide();
            $('<button>')
                .addClass('clear-button')
                .text('Show All Sources')
                .css({ 'margin-top': '0.5rem', 'width': 'auto', 'padding': '0.5rem' })
                .appendTo($sourceLegend)
                .on('click', function() {
                    $legendItems.slice(6).toggle();
                    $(this).text($(this).text() === 'Show All Sources' ? 'Show Less' : 'Show All Sources');
                });
        }
    }

    // Simplify search topic (restored from original)
    function simplifySearchTopic(topic) {
        const removeWords = ['and', 'the', 'by', 'from', 'to', 'in', 'on', 'at', 'for', 'of'];
        const specialCases = {
            'administration': 'admin', 'president': '', 'impeached': 'impeach',
            'released': 'release', 'imposes': 'impose', 'sanctions': 'sanction'
        };
        
        let words = topic.split(' ').filter(word => !removeWords.includes(word.toLowerCase()));
        words = words.map(word => specialCases[word.toLowerCase()] || word);
        
        if (words.length > 3) {
            const properNouns = words.filter(word => word[0] === word[0].toUpperCase());
            const keyTerms = words.filter(word => word[0] !== word[0].toUpperCase());
            words = [...properNouns, ...keyTerms.slice(0, 2)];
        }
        
        const simplified = words.filter(word => word).join(' ');
        console.log(`Simplified topic "${topic}" to "${simplified}"`);
        return simplified;
    }

    // Display articles and image
    function displayArticles(articles, summary, metadata) {
        const responseTime = new Date() - window.requestStartTime;
        Analytics.trackAPIResponse('/data', responseTime, !!articles && articles.length > 0);
        
        console.log('displayArticles called with:', {
            articlesCount: articles ? articles.length : 0,
            summary: summary,
            metadata: metadata
        });
        
        $loading.hide();
        if (articles && articles.length > 0) {
            let articlesHtml = articles.map(article => {
                return `
                    <div class="article-card">
                        <h3 class="article-title">
                            <a href="${article.url}" target="_blank" rel="noopener noreferrer" class="article-link">
                                ${article.title}
                            </a>
                        </h3>
                        <div class="article-meta">
                            <span class="source">${article.source}</span>
                            ${article.published_at ? `<span class="article-date"> • ${new Date(article.published_at).toLocaleDateString()}</span>` : ''}
                        </div>
                        <p class="article-content">${article.content}</p>
                        <div class="sentiment-bar">
                            <div class="sentiment-indicator" style="
                                width: ${getSentimentWidth(article.sentiment_score)};
                                background-color: ${getSentimentColor(article.sentiment_score)};
                            "></div>
                        </div>
                        <div class="sentiment-label">${getSentimentLabel(article.sentiment_score)}</div>
                    </div>
                `;
            }).join('');
            
            $results.find('.article-list').html(articlesHtml);
            $results.find('.summary-card .summary-content').html(summary);
            
            console.log('After update:', {
                summaryContent: $results.find('.summary-card .summary-content').html(),
                summaryCardVisible: $results.find('.summary-card').is(':visible')
            });
            
            $results.find('#articles-analyzed').text(articles.length);
            $results.find('#average-sentiment').text(getSentimentLabel(metadata.average_sentiment));
            $results.find('#sentiment-gauge-indicator').css({
                'width': getSentimentWidth(metadata.average_sentiment),
                'background-color': getSentimentColor(metadata.average_sentiment)
            });
            
            if (metadata.source_distribution) {
                createSourceDistribution(metadata.source_distribution);
                $results.find('.source-dashboard').show();
            } else {
                $results.find('.source-dashboard').hide();
            }
            
            // When image data is in the response
            if (metadata && metadata.image && metadata.image.path) {
                console.log("Raw image path received:", metadata.image.path);
                console.log('Displaying image from metadata:', metadata.image.path);
                
                // Parse the image path to create responsive image paths
                const imagePath = metadata.image.path;
                const lastDotIndex = imagePath.lastIndexOf('.');
                const imageBase = imagePath.substring(0, lastDotIndex);
                const imageExt = imagePath.substring(lastDotIndex + 1);
                
                // Create picture element for responsive images
                const pictureElement = $('<picture>');
                
                // Add WebP source with responsive sizes
                const webpSource = $('<source>')
                    .attr('type', 'image/webp')
                    .attr('srcset', `${imageBase}_400.webp 400w, ${imageBase}_800.webp 800w, ${imagePath} 1024w`)
                    .attr('sizes', '(max-width: 600px) 400px, (max-width: 1200px) 800px, 1024px');
                
                // Add fallback source with responsive sizes
                const fallbackSource = $('<source>')
                    .attr('srcset', `${imageBase}_400.${imageExt} 400w, ${imageBase}_800.${imageExt} 800w, ${imagePath} 1024w`)
                    .attr('sizes', '(max-width: 600px) 400px, (max-width: 1200px) 800px, 1024px');
                
                // Create the image element (fallback)
                const imgElement = $('<img>')
                    .attr('src', imagePath)
                    .attr('alt', 'News topic visualization')
                    .attr('class', 'responsive-image')
                    .attr('loading', 'lazy')
                    .css({
                        'max-width': '100%',
                        'height': 'auto',
                        'display': 'block'
                    })
                    .on('error', function(e) {
                        console.error('Image load failed:', imagePath, 'Error details:', e);
                        console.error('Image element state:', this);
                        $imageContainer.html('<p>Image failed to load.</p>');
                    })
                    .on('load', function() {
                        console.log('Image loaded successfully:', imagePath);
                    });
                
                // Assemble the picture element
                pictureElement.append(webpSource).append(fallbackSource).append(imgElement);
                
                // Update container and show it
                $imageContainer.html(pictureElement).show();
                console.log('Image container updated with responsive picture element');
            } else {
                console.log('No image path in metadata');
                $imageContainer.html('<p>No image available.</p>').show();
            }
            
            $results.show();
            $results.find('.summary-card').show();
            $results.find('.articles-card').show();
            $results.find('.clear-button').show();
            $results.find('.sentiment-summary').show();
        } else {
            console.log('No articles found, showing error message');
            $errorMessage.text('No articles found.').show();
            $imageContainer.hide();
        }
    }

    // Handle trending card clicks
    $('.trending-card').on('click', function() {
        console.log('Trending card click event triggered');
        const searchTerm = $(this).data('search-term');
        console.log('Original search term:', searchTerm);
        
        if (!searchTerm) {
            console.error('No search term found for this topic');
            return;
        }
        
        // Track the hot topic click with analytics
        const category = $(this).closest('.topic-column').data('category') || 'unknown';
        Analytics.trackHotTopicClick(searchTerm, category);

        $loading.show();
        $results.hide();
        $errorMessage.text('').hide();
        $results.find('.summary-card').hide();
        $results.find('.articles-card').hide();
        $results.find('.clear-button').hide();
        $results.find('.sentiment-summary').hide();
        $results.find('.source-dashboard').hide();
        $trendingContainer.hide();
        $imageContainer.hide();

        // Get the image toggle state
        const includeImages = $('#image-toggle').is(':checked');
        console.log('Image toggle state (trending card):', includeImages);
        
        // Hide image container initially
        $imageContainer.hide();
        
        // Make the AJAX request with the properly formatted include_images parameter
        const formData = {
            event: searchTerm,
            include_images: includeImages ? 'true' : 'false' // Standardize to string format
        };
        console.log('Sending form data (trending card):', formData);
        
        $.post('/data', formData, function(data) {
            console.log('Received response with include_images:', includeImages);
            console.log('Response received:', data);
            if (data.error) {
                console.log('Error found in response:', data.error);
                $errorMessage.text(data.error).show();
                
                // Still display any articles/summary if available despite errors
                if (data.articles && data.articles.length > 0) {
                    displayArticles(data.articles, data.summary || '', data.metadata || {});
                }
            } else {
                $results.find('.current-topic').text('Current topic: ' + searchTerm).show();
                console.log('Articles:', data.articles ? data.articles.length : 0);
                console.log('Summary:', data.summary);
                console.log('Metadata:', data.metadata);
                
                if (data.warning) {
                    if (!data.articles || data.articles.length === 0) {
                        $errorMessage.text(data.warning).show();
                    } else {
                        $errorMessage.hide();
                    }
                } else {
                    $errorMessage.hide();
                }
                displayArticles(data.articles, data.summary, data.metadata || {});
            }
        }).fail(function(jqXHR, textStatus, errorThrown) {
            console.error('AJAX request failed:', textStatus, errorThrown, jqXHR.status);
            
            if (jqXHR.status === 503) {
                $errorMessage.html("Our news sources are temporarily unavailable. Please try again in a few minutes.<br><small>This is often due to rate limits on our news APIs.</small>").show();
            } else {
                $errorMessage.text('Failed to fetch results. Please try again.').show();
            }
            
            // Create empty placeholder results
            displayArticles([], "Unable to retrieve news at this time.", {
                average_sentiment: 0,
                source_distribution: {},
                image: null
            });
        }).always(function() {
            $loading.hide();
            $results.show();
        });
    });

    // Handle search form submission
    $('#search-form').submit(function(event) {
        event.preventDefault();
        var eventQuery = $('input[name="event"]', this).val();
        if (!eventQuery) {
            alert('Please enter a news event to search for.');
            return;
        }
        
        // Track the manual search
        Analytics.trackSearch(eventQuery);
        
        $loading.show();
        $results.hide();
        $errorMessage.text('').hide();
        $results.find('.summary-card').hide();
        $results.find('.articles-card').hide();
        $results.find('.clear-button').hide();
        $results.find('.sentiment-summary').hide();
        $results.find('.source-dashboard').hide();
        $trendingContainer.hide();
        $imageContainer.hide();

        // Get the image toggle state
        const includeImages = $('#image-toggle').is(':checked');
        console.log('Image toggle state:', includeImages);
        
        // Hide image container initially
        $imageContainer.hide();
        
        // Make the AJAX request with the properly formatted include_images parameter
        const formData = {
            event: eventQuery,
            include_images: includeImages ? 'true' : 'false' // Standardize to string format
        };
        console.log('Sending form data:', formData);
        
        $.post('/data', formData, function(data) {
            console.log('Received response with include_images:', includeImages);
            console.log('Response received:', data);
            if (data.error) {
                console.log('Error found in response:', data.error);
                $errorMessage.text(data.error).show();
                
                // Still display any articles/summary if available despite errors
                if (data.articles && data.articles.length > 0) {
                    displayArticles(data.articles, data.summary || '', data.metadata || {});
                }
            } else {
                $results.find('.current-topic').text('Current topic: ' + eventQuery).show();
                console.log('Articles:', data.articles ? data.articles.length : 0);
                console.log('Summary:', data.summary);
                console.log('Metadata:', data.metadata);
                
                if (data.warning) {
                    if (!data.articles || data.articles.length === 0) {
                        $errorMessage.text(data.warning).show();
                    } else {
                        $errorMessage.hide();
                    }
                } else {
                    $errorMessage.hide();
                }
                displayArticles(data.articles, data.summary, data.metadata || {});
            }
        }).fail(function(jqXHR, textStatus, errorThrown) {
            console.error('AJAX request failed:', textStatus, errorThrown, jqXHR.status);
            
            if (jqXHR.status === 503) {
                $errorMessage.html("Our news sources are temporarily unavailable. Please try again in a few minutes.<br><small>This is often due to rate limits on our news APIs.</small>").show();
            } else {
                $errorMessage.text('Failed to fetch results. Please try again.').show();
            }
            
            // Create empty placeholder results
            displayArticles([], "Unable to retrieve news at this time.", {
                average_sentiment: 0,
                source_distribution: {},
                image: null
            });
        }).always(function() {
            $loading.hide();
            $results.show();
        });
    });

    // Clear button handler
    $results.find('.clear-button').on('click', function() {
        $('.topic-image-card').hide();
        $('.image-loading').hide();
        $('.image-error').hide();
        $('#topic-image').hide();
        $imageContainer.hide();
        window.location.href = "/";
    });

    // Logo click handler
    $('.logo').on('click', function() {
        $('.search-input').val('');
        $('#results').hide();
        $('.trending-container').show();
        $('.current-topic').hide();
        $('.error-message').hide();
        $imageContainer.hide();
        document.title = 'Neutral News';
    });

    // Track article clicks
    $(document).on('click', '.article-link', function(e) {
        const $article = $(this).closest('.article-card');
        Analytics.trackArticleClick({
            title: $(this).text(),
            source: $article.find('.source').text(),
            url: $(this).attr('href')
        });
    });
    
    // Track feature views
    $('.summary-card').on('inview', function() {
        Analytics.trackFeatureView('summary');
    });
    
    $('#image-container').on('inview', function() {
        Analytics.trackFeatureView('visualization');
    });
    
    $('.articles-card').on('inview', function() {
        Analytics.trackFeatureView('articles');
    });
});