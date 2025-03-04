console.log('main.js loaded');
$(document).ready(function() {
    console.log('jQuery ready');
    // Verify form exists
    console.log('Search form exists:', $('#search-form').length > 0);
    var $loading = $('.loading');
    var $results = $('#results');
    var $errorMessage = $results.find('.error-message');
    var $pullIndicator = $('.pull-indicator');
    var startY = 0;
    var pullThreshold = 80;
    var isPulling = false;
    
    // Pull to refresh functionality for mobile
    document.addEventListener('touchstart', function(e) {
        startY = e.touches[0].clientY;
        
        // Only enable pull-to-refresh when at the top of the page
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
            // Refresh the page
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
    
    function getSentimentColor(score) {
        // Convert score (-1 to 1) to a color
        if (score === 0) return '#e2e8f0';  // Neutral gray
        
        let red, green, blue;
        if (score < 0) {
            // Negative: red to gray
            let factor = 1 + score;  // Convert -1..0 to 0..1
            red = 239;  // #ef4444
            green = Math.round(68 + (148 * factor));
            blue = Math.round(68 + (148 * factor));
        } else {
            // Positive: gray to blue
            let factor = score;  // Already 0..1
            red = Math.round(226 - (127 * factor));
            green = Math.round(232 - (111 * factor));
            blue = Math.round(240 + (15 * factor));
        }
        return `rgb(${red}, ${green}, ${blue})`;
    }
    
    function getSentimentWidth(score) {
        // Convert score (-1 to 1) to width percentage (20% to 100%)
        return 20 + (Math.abs(score) * 80) + '%';
    }
    
    function getSentimentLabel(score) {
        if (Math.abs(score) < 0.2) return "Neutral";
        if (score < -0.6) return "Very Negative";
        if (score < -0.2) return "Somewhat Negative";
        if (score > 0.6) return "Very Positive";
        if (score > 0.2) return "Somewhat Positive";
        return "Neutral";
    }
    
    // Generate a color for each source
    function getSourceColor(sourceName, index) {
        // Predefined colors for common news sources
        const sourceColors = {
            'BBC News': '#BB1919',
            'CNN': '#CC0000',
            'Fox News': '#003366',
            'The Guardian': '#052962',
            'The New York Times': '#000000',
            'Reuters': '#FF8000',
            'Associated Press': '#FF0000',
            'Washington Post': '#000000',
            'CNBC': '#005594',
            'Bloomberg': '#000000'
        };
        
        if (sourceColors[sourceName]) {
            return sourceColors[sourceName];
        }
        
        // Generate colors based on index for other sources
        const hue = (index * 137.5) % 360; // Golden angle approximation for good distribution
        return `hsl(${hue}, 70%, 50%)`;
    }
    
    // Calculate balance score based on source distribution
    function calculateBalanceScore(sourceDistribution) {
        if (!sourceDistribution || Object.keys(sourceDistribution).length === 0) {
            return 0;
        }
        
        const sourceCount = Object.keys(sourceDistribution).length;
        const totalArticles = Object.values(sourceDistribution).reduce((sum, count) => sum + count, 0);
        
        // Perfect distribution would be 1/sourceCount for each source
        const idealPercentage = 1 / sourceCount;
        
        // Calculate how far each source is from the ideal percentage
        let totalDeviation = 0;
        for (const source in sourceDistribution) {
            const actualPercentage = sourceDistribution[source] / totalArticles;
            totalDeviation += Math.abs(actualPercentage - idealPercentage);
        }
        
        // Normalize to 0-100 scale (0 = completely unbalanced, 100 = perfectly balanced)
        // Max possible deviation is 2 - (2/sourceCount)
        const maxDeviation = 2 - (2 / sourceCount);
        const balanceScore = 100 * (1 - (totalDeviation / maxDeviation));
        
        return Math.round(balanceScore);
    }
    
    // Create source distribution visualization
    function createSourceDistribution(sourceDistribution) {
        if (!sourceDistribution || Object.keys(sourceDistribution).length === 0) {
            return;
        }
        
        const $sourceChart = $('#source-chart');
        const $sourceLegend = $('#source-legend');
        
        $sourceChart.empty();
        $sourceLegend.empty();
        
        const sources = Object.keys(sourceDistribution);
        const totalArticles = Object.values(sourceDistribution).reduce((sum, count) => sum + count, 0);
        
        // Update source count
        $('#source-count').text(sources.length);
        
        // Calculate and update balance score
        const balanceScore = calculateBalanceScore(sourceDistribution);
        $('#balance-score').text(balanceScore + '/100');
        
        // Create bars and legend items
        sources.forEach((source, index) => {
            const count = sourceDistribution[source];
            const percentage = Math.round((count / totalArticles) * 100);
            const height = Math.max(20, percentage * 2); // Min height 20px, max 200px
            const color = getSourceColor(source, index);
            
            // Create bar with tooltip
            const $bar = $('<div>')
                .addClass('source-bar tooltip')
                .css({
                    'height': height + 'px',
                    'background-color': color
                })
                .appendTo($sourceChart);
            
            // Add percentage label
            $('<div>')
                .addClass('source-percentage')
                .text(percentage + '%')
                .appendTo($bar);
                
            // Add tooltip
            $('<span>')
                .addClass('tooltip-text')
                .text(`${source}: ${count} articles (${percentage}%)`)
                .appendTo($bar);
            
            // Create legend item
            const $legendItem = $('<div>')
                .addClass('legend-item')
                .appendTo($sourceLegend);
            
            $('<div>')
                .addClass('legend-color')
                .css('background-color', color)
                .appendTo($legendItem);
            
            $('<div>')
                .addClass('legend-label')
                .text(`${source} (${count})`)
                .appendTo($legendItem);
        });
        
        // Add responsive behavior for mobile
        if (window.innerWidth <= 640) {
            // Limit the number of visible legend items on mobile
            const $legendItems = $sourceLegend.find('.legend-item');
            if ($legendItems.length > 6) {
                // Hide excess items and add a "show more" button
                $legendItems.slice(6).hide();
                
                const $showMoreBtn = $('<button>')
                    .addClass('clear-button')
                    .text('Show All Sources')
                    .css({
                        'margin-top': '0.5rem',
                        'width': 'auto',
                        'padding': '0.5rem'
                    })
                    .appendTo($sourceLegend);
                    
                $showMoreBtn.on('click', function() {
                    $legendItems.slice(6).toggle();
                    $(this).text($(this).text() === 'Show All Sources' ? 'Show Less' : 'Show All Sources');
                });
            }
        }
    }

    function displayArticles(articles, summary, metadata) {
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
            $results.find('#articles-analyzed').text(articles.length);
            $results.find('#average-sentiment').text(getSentimentLabel(metadata.average_sentiment));
            $results.find('#sentiment-gauge-indicator').css({
                'width': getSentimentWidth(metadata.average_sentiment),
                'background-color': getSentimentColor(metadata.average_sentiment)
            });
            
            // Create source distribution visualization
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
            $results.find('.sentiment-summary').show();
        } else {
            $errorMessage.text('No articles found.').show();
        }
    }

    $('#search-form').submit(function(event) {
        event.preventDefault();
        var eventQuery = $('input[name="event"]', this).val();
        if (!eventQuery) {
            alert('Please enter a news event to search for.');
            return;
        }
        $loading.show();
        $results.hide();
        $errorMessage.text('').hide();
        $results.find('.summary-card').hide();
        $results.find('.articles-card').hide();
        $results.find('.clear-button').hide();
        $results.find('.sentiment-summary').hide();
        $results.find('.source-dashboard').hide();

        $.post('/data', {event: eventQuery}, function(data) {
            if (data.error) {
                $errorMessage.text(data.error).show();
            } else {
                $results.find('.current-topic').text('Current topic: ' + eventQuery).show();
                if (data.warning) {
                    // Only show warning if no articles were found
                    if (!data.articles || data.articles.length === 0) {
                        $errorMessage.text(data.warning).show();
                    } else {
                        $errorMessage.hide();
                    }
                } else {
                    $errorMessage.hide();
                }
                displayArticles(data.articles, data.summary, data.metadata);
            }
        }).fail(function(jqXHR, textStatus, errorThrown) {
            if (textStatus === 'timeout') {
                $errorMessage.text('Request timed out. Please try again later.').show();
            } else {
                $errorMessage.text('An error occurred: ' + textStatus + ' - ' + errorThrown).show();
            }
        }).always(function() {
            $loading.hide();
        });
    });

    $results.find('.clear-button').on('click', function() {
        window.location.href = "/";
    });
}); 