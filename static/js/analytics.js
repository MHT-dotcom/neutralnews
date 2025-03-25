// Analytics tracking
const Analytics = {
    // Session data
    sessionStart: new Date(),
    lastInteraction: new Date(),
    pageLoaded: new Date(),
    interactions: 0,
    articleClicks: 0,
    maxScroll: 0,

    // Initialize analytics
    init: function() {
        this.trackPageLoad();
        this.setupScrollTracking();
        this.setupExitTracking();
    },

    // Track page load performance
    trackPageLoad: function() {
        const timing = window.performance.timing;
        const loadTime = timing.loadEventEnd - timing.navigationStart;
        this.logMetric('page_load', {
            load_time_ms: loadTime,
            url: window.location.href,
            user_agent: navigator.userAgent,
            viewport: `${window.innerWidth}x${window.innerHeight}`
        });
    },

    // Track search queries
    trackSearch: function(query) {
        this.interactions++;
        this.lastInteraction = new Date();
        this.logMetric('search', {
            query: query,
            timestamp: new Date().toISOString()
        });
    },

    // Track hot topic clicks
    trackHotTopicClick: function(topic, category) {
        this.interactions++;
        this.lastInteraction = new Date();
        this.logMetric('hot_topic_click', {
            topic: topic,
            category: category, // 'today', 'last_week', 'last_month'
            timestamp: new Date().toISOString()
        });
    },

    // Track article interactions
    trackArticleClick: function(articleData) {
        this.articleClicks++;
        this.interactions++;
        this.lastInteraction = new Date();
        this.logMetric('article_click', {
            title: articleData.title,
            source: articleData.source,
            timestamp: new Date().toISOString()
        });
    },

    // Track scroll depth
    setupScrollTracking: function() {
        let ticking = false;
        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    const scrollPercent = Math.round((window.scrollY + window.innerHeight) / document.documentElement.scrollHeight * 100);
                    if (scrollPercent > this.maxScroll) {
                        this.maxScroll = scrollPercent;
                        this.logMetric('scroll_depth', {
                            depth_percentage: this.maxScroll,
                            timestamp: new Date().toISOString()
                        });
                    }
                    ticking = false;
                });
                ticking = true;
            }
        });
    },

    // Track session data on exit
    setupExitTracking: function() {
        window.addEventListener('beforeunload', () => {
            const sessionDuration = new Date() - this.sessionStart;
            this.logMetric('session_end', {
                duration_ms: sessionDuration,
                interactions: this.interactions,
                article_clicks: this.articleClicks,
                max_scroll_depth: this.maxScroll,
                timestamp: new Date().toISOString()
            });
        });
    },

    // Track API response times
    trackAPIResponse: function(endpoint, responseTime, success, errorMessage = null) {
        this.logMetric('api_response', {
            endpoint: endpoint,
            response_time_ms: responseTime,
            success: success,
            error: errorMessage,
            timestamp: new Date().toISOString()
        });
    },

    // Track feature usage
    trackFeatureView: function(feature) {
        this.interactions++;
        this.lastInteraction = new Date();
        this.logMetric('feature_view', {
            feature: feature, // 'summary', 'visualization', 'articles'
            timestamp: new Date().toISOString()
        });
    },

    // Log metrics to backend
    logMetric: function(eventType, data) {
        fetch('/analytics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                event_type: eventType,
                data: data
            })
        }).catch(error => console.error('Analytics error:', error));
    }
};

// Initialize analytics when the script loads
Analytics.init(); 