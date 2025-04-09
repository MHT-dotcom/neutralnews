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
    
    // Source color utility
    function getSourceColor(sourceName, index) {
        // Predefined colors for major news sources
        const sourceColors = {
            'BBC News': '#BB1919', 
            'CNN': '#CC0000', 
            'Fox News': '#003366',
            'Guardian': '#052962', 
            'The Guardian': '#052962',
            'New York Times': '#000000',
            'The New York Times': '#000000',
            'Reuters': '#FF8000', 
            'Associated Press': '#0C4B86',
            'AP': '#0C4B86',
            'Washington Post': '#1955A5', 
            'CNBC': '#005594', 
            'Bloomberg': '#000000',
            'ABC News': '#0976B4',
            'NBC News': '#5A83B1',
            'CBS News': '#000000',
            'USA Today': '#0078BE',
            'Wall Street Journal': '#173B67',
            'Breitbart': '#A91100',
            'Breitbart News': '#A91100',
            'Business Insider': '#2668B0',
            'NPR': '#D62021',
            'The Times of India': '#E34925',
            'Gizmodo': '#00AEEF',
            'Gizmodo.com': '#00AEEF',
            'The Verge': '#5F9DF7',
            'Wired': '#95ADC0',
            'Newsweek': '#FF0500'
        };
        
        // Return predefined color if available
        if (sourceColors[sourceName]) {
            return sourceColors[sourceName];
        }
        
        // Generate a vibrant color based on index
        // Using a golden ratio approach for better distribution
        const hue = (index * 137.5) % 360; // Golden ratio approximation
        return `hsl(${hue}, 75%, 45%)`;
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
        
        // Process the source distribution to handle object-like strings
        const processedDistribution = {};
        for (const source in sourceDistribution) {
            let sourceName = source;
            
            // Handle string that looks like object
            if (typeof sourceName === 'string' && sourceName.startsWith('{') && sourceName.includes('name')) {
                try {
                    // Try to extract using regex first
                    const nameMatch = sourceName.match(/['"]name['"]:\s*['"]([^'"]+)['"]/);
                    if (nameMatch && nameMatch[1]) {
                        sourceName = nameMatch[1];
                    } else {
                        // Try parsing as JSON if regex fails
                        const sourceObj = JSON.parse(sourceName.replace(/'/g, '"'));
                        if (sourceObj && sourceObj.name) {
                            sourceName = sourceObj.name;
                        }
                    }
                } catch (e) {
                    console.error('Error parsing source object string:', e);
                }
            }
            
            // Add to processed distribution, combining counts for same source
            if (processedDistribution[sourceName]) {
                processedDistribution[sourceName] += sourceDistribution[source];
            } else {
                processedDistribution[sourceName] = sourceDistribution[source];
            }
        }
        
        const sources = Object.keys(processedDistribution);
        const totalArticles = Object.values(processedDistribution).reduce((sum, count) => sum + count, 0);
        
        $('#source-count').text(sources.length);
        const balanceScore = calculateBalanceScore(processedDistribution);
        $('#balance-score').text(balanceScore + '/100');
        
        // Sort sources by count for better visualization
        const sortedSources = sources.sort((a, b) => processedDistribution[b] - processedDistribution[a]);
        
        sortedSources.forEach((source, index) => {
            const count = processedDistribution[source];
            const percentage = Math.round((count / totalArticles) * 100);
            const height = Math.max(30, percentage * 2); // Minimum height of 30px
            const color = getSourceColor(source, index);
            
            // Create the bar with appropriate height and color
            const $bar = $('<div>')
                .addClass('source-bar tooltip')
                .css({ 
                    'height': height + 'px', 
                    'background-color': color,
                    'flex-grow': count, // Make wider bars for sources with more articles
                })
                .appendTo($sourceChart);
            
            // Add percentage label to each bar
            $('<div>').addClass('source-percentage').text(percentage + '%').appendTo($bar);
            
            // Add tooltip with detailed information
            $('<span>').addClass('tooltip-text').text(`${source}: ${count} articles (${percentage}%)`).appendTo($bar);
            
            // Create legend item
            const $legendItem = $('<div>').addClass('legend-item').appendTo($sourceLegend);
            $('<div>').addClass('legend-color').css('background-color', color).appendTo($legendItem);
            $('<div>').addClass('legend-label').text(`${source} (${count})`).appendTo($legendItem);
        });
        
        // Show/hide toggle for mobile
        if (window.innerWidth <= 640 && sources.length > 6) {
            const $legendItems = $sourceLegend.find('.legend-item');
            $legendItems.slice(6).hide();
            
            // Check if button already exists
            if (!$sourceLegend.find('.show-all-button').length) {
                $('<button>')
                    .addClass('show-all-button')
                    .text('Show All Sources')
                    .css({ 
                        'margin-top': '0.5rem', 
                        'width': 'auto', 
                        'padding': '0.5rem',
                        'background-color': 'var(--accent)',
                        'color': 'white',
                        'border': 'none',
                        'border-radius': '4px',
                        'cursor': 'pointer'
                    })
                    .appendTo($sourceLegend)
                    .on('click', function() {
                        $legendItems.slice(6).toggle();
                        $(this).text($(this).text() === 'Show All Sources' ? 'Show Less' : 'Show All Sources');
                    });
            }
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
                // Extract source name if it's an object or an object string
                let sourceName = article.source;
                
                // Handle if sourceName is a string that looks like an object
                if (typeof sourceName === 'string' && sourceName.startsWith('{') && sourceName.includes('name')) {
                    try {
                        // Try to extract using regex first
                        const nameMatch = sourceName.match(/['"]name['"]:\s*['"]([^'"]+)['"]/);
                        if (nameMatch && nameMatch[1]) {
                            sourceName = nameMatch[1];
                        } else {
                            // Try parsing as JSON if regex fails
                            const sourceObj = JSON.parse(sourceName.replace(/'/g, '"'));
                            if (sourceObj && sourceObj.name) {
                                sourceName = sourceObj.name;
                            }
                        }
                    } catch (e) {
                        console.error('Error parsing source object string:', e);
                    }
                }
                // Handle if sourceName is an actual object
                else if (typeof sourceName === 'object' && sourceName !== null) {
                    sourceName = sourceName.name || sourceName.title || 'Unknown Source';
                }
                
                return `
                    <div class="article-card">
                        <h3 class="article-title">
                            <a href="${article.url}" target="_blank" rel="noopener noreferrer" class="article-link">
                                ${article.title}
                            </a>
                        </h3>
                        <div class="article-meta">
                            <span class="source">${sourceName}</span>
                            ${article.published_at ? `<span class="article-date"> • ${new Date(article.published_at).toLocaleDateString()}</span>` : ''}
                        </div>
                        <p class="article-content">${article.content}</p>
                    </div>
                `;
            }).join('');
            
            $results.find('.article-list').html(articlesHtml);
            $results.find('.summary-card .summary-content').html(summary);
            
            console.log('After update:', {
                summaryContent: $results.find('.summary-card .summary-content').html(),
                summaryCardVisible: $results.find('.summary-card').is(':visible')
            });
            
            if (metadata.source_distribution) {
                createSourceDistribution(metadata.source_distribution);
                $results.find('.source-dashboard').show();
            } else {
                $results.find('.source-dashboard').hide();
            }
            
            $results.show();
            $results.find('.summary-card').show();
            $results.find('.articles-card').show();
            $results.find('.clear-button').show();
        } else {
            console.log('No articles found, showing error message');
            $errorMessage.text('No articles found.').show();
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
        $results.find('.source-dashboard').hide();
        $trendingContainer.hide();
        
        // Make the AJAX request
        const formData = {
            event: searchTerm
        };
        console.log('Sending form data (trending card):', formData);
        
        $.post('/data', formData, function(data) {
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
        $results.find('.source-dashboard').hide();
        $trendingContainer.hide();
        
        // Make the AJAX request
        const formData = {
            event: eventQuery
        };
        console.log('Sending form data:', formData);
        
        $.post('/data', formData, function(data) {
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
        window.location.href = "/";
    });

    // Logo click handler
    $('.logo').on('click', function() {
        $('.search-input').val('');
        $('#results').hide();
        $('.trending-container').show();
        $('.current-topic').hide();
        $('.error-message').hide();
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
    
    $('.articles-card').on('inview', function() {
        Analytics.trackFeatureView('articles');
    });
});