import os
import asyncio
import aiohttp
import re
from datetime import datetime, timedelta
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import random
import json

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Store tracked wallets in memory
user_preferences = {}

# Trending data cache
trending_cache = {
    'google_trends': [],
    'reddit_trending': [],
    'coingecko_trending': [],
    'youtube_trending': [],
    'twitter_trends': [],
    'crypto_news': [],
    'last_update': None
}

# ============ TREND MONITORING FUNCTIONS ============

async def fetch_youtube_trending():
    """Fetch trending videos from YouTube (no API key needed)"""
    try:
        # YouTube trending page scraping
        url = "https://www.youtube.com/feed/trending"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    text = await response.text()
                    # Extract video titles (simplified)
                    titles = re.findall(r'"title":{"runs":\[{"text":"([^"]+)"}\]', text)
                    # Filter out YouTube UI text and get unique titles
                    trending = [t for t in titles if len(t) > 10 and not t.startswith('YouTube')][:15]
                    print(f"✅ Got {len(trending)} trending videos from YouTube")
                    return trending
    except Exception as e:
        print(f"YouTube trending failed: {e}")
    return []

async def fetch_twitter_alternative():
    """Fetch trending topics using Nitter (Twitter mirror - FREE)"""
    try:
        # Nitter instances are free Twitter mirrors
        nitter_instances = [
            "https://nitter.net",
            "https://nitter.privacydev.net",
            "https://nitter.poast.org"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for instance in nitter_instances:
            try:
                url = f"{instance}/explore"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            text = await response.text()
                            # Extract trending topics
                            trends = re.findall(r'<span class="trend-name">([^<]+)</span>', text)
                            if trends:
                                print(f"✅ Got {len(trends)} trends from Twitter (via {instance})")
                                return trends[:10]
            except Exception as e:
                print(f"Nitter instance {instance} failed: {e}")
                continue
    except Exception as e:
        print(f"Twitter alternative failed: {e}")
    return []

async def fetch_crypto_news():
    """Fetch latest crypto news headlines (FREE)"""
    try:
        # CoinTelegraph RSS feed
        url = "https://cointelegraph.com/rss"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    text = await response.text()
                    # Extract titles
                    titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', text)
                    if len(titles) > 1:
                        print(f"✅ Got {len(titles)-1} crypto news headlines")
                        return titles[1:11]  # Skip first (feed title)
    except Exception as e:
        print(f"Crypto news failed: {e}")
    return []

async def fetch_google_trends():
    """Fetch trending searches using multiple fallback methods"""
    trends = []
    
    # Method 1: Try Google Trends RSS (simple)
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    text = await response.text()
                    matches = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', text)
                    if len(matches) > 1:
                        trends = matches[1:11]
                        print(f"✅ Got {len(trends)} trends from Google RSS")
                        return trends
    except Exception as e:
        print(f"Google Trends RSS failed: {e}")
    
    # Method 2: Use hardcoded popular crypto/trending topics as fallback
    fallback_trends = [
        "Bitcoin", "Ethereum", "Solana", "AI Technology",
        "Cryptocurrency News", "Memecoin", "DeFi",
        "NFT Market", "Blockchain", "Web3"
    ]
    
    print("⚠️ Using fallback trending topics")
    return fallback_trends[:10]

async def fetch_reddit_trending():
    """Fetch trending posts from crypto subreddits"""
    try:
        subreddits = ['cryptocurrency', 'solana', 'CryptoMoonShots']
        all_trends = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            for subreddit in subreddits:
                try:
                    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5"
                    
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            data = await response.json()
                            posts = data.get('data', {}).get('children', [])
                            
                            for post in posts:
                                post_data = post.get('data', {})
                                all_trends.append({
                                    'title': post_data.get('title', ''),
                                    'score': post_data.get('score', 0),
                                    'subreddit': subreddit,
                                    'url': f"https://reddit.com{post_data.get('permalink', '')}"
                                })
                        
                        await asyncio.sleep(2)  # Be nice to Reddit
                except Exception as e:
                    print(f"Error fetching r/{subreddit}: {e}")
                    continue
        
        # Sort by score
        all_trends.sort(key=lambda x: x['score'], reverse=True)
        print(f"✅ Got {len(all_trends)} posts from Reddit")
        return all_trends[:10]
        
    except Exception as e:
        print(f"Error fetching Reddit: {e}")
    return []

async def fetch_coingecko_trending():
    """Fetch trending coins from CoinGecko (FREE API)"""
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    coins = data.get('coins', [])
                    
                    trending = []
                    for coin in coins[:10]:
                        item = coin.get('item', {})
                        trending.append({
                            'name': item.get('name', ''),
                            'symbol': item.get('symbol', ''),
                            'market_cap_rank': item.get('market_cap_rank', 'N/A'),
                            'price_btc': item.get('price_btc', 0)
                        })
                    
                    print(f"✅ Got {len(trending)} trending coins from CoinGecko")
                    return trending
    except Exception as e:
        print(f"Error fetching CoinGecko: {e}")
    return []

async def update_trending_data():
    """Update all trending data from free sources"""
    print("📊 Updating trending data from ALL sources...")
    
    # Fetch all sources in parallel
    results = await asyncio.gather(
        fetch_google_trends(),
        fetch_reddit_trending(),
        fetch_coingecko_trending(),
        fetch_youtube_trending(),
        fetch_twitter_alternative(),
        fetch_crypto_news(),
        return_exceptions=True
    )
    
    google_trends = results[0] if not isinstance(results[0], Exception) else []
    reddit_trends = results[1] if not isinstance(results[1], Exception) else []
    coingecko_trends = results[2] if not isinstance(results[2], Exception) else []
    youtube_trends = results[3] if not isinstance(results[3], Exception) else []
    twitter_trends = results[4] if not isinstance(results[4], Exception) else []
    crypto_news = results[5] if not isinstance(results[5], Exception) else []
    
    trending_cache['google_trends'] = google_trends
    trending_cache['reddit_trending'] = reddit_trends
    trending_cache['coingecko_trending'] = coingecko_trends
    trending_cache['youtube_trending'] = youtube_trends
    trending_cache['twitter_trends'] = twitter_trends
    trending_cache['crypto_news'] = crypto_news
    trending_cache['last_update'] = datetime.now()
    
    total = len(google_trends) + len(reddit_trends) + len(coingecko_trends) + len(youtube_trends) + len(twitter_trends) + len(crypto_news)
    print(f"✅ Total data points collected: {total}")

# ============ COIN IDEA GENERATOR ============

def generate_coin_name(trend):
    """Generate memecoin name from trend"""
    # Clean the trend
    clean_trend = re.sub(r'[^a-zA-Z0-9\s]', '', trend)
    words = clean_trend.split()
    
    # Different naming patterns
    patterns = [
        f"{words[0]}Coin" if words else "TrendCoin",
        f"{words[0]}Token" if words else "TrendToken",
        f"{''.join(words[:2])}" if len(words) >= 2 else trend,
        f"{words[0]}Inu" if words else "TrendInu",
        f"Baby{words[0]}" if words else "BabyTrend",
        f"{words[0]}Moon" if words else "MoonTrend",
    ]
    
    return random.choice(patterns)

def generate_ticker(name):
    """Generate ticker symbol"""
    # Take first letters or abbreviate
    clean = re.sub(r'[^A-Z]', '', name.upper())
    if len(clean) >= 3:
        return clean[:4]
    else:
        return (name[:4].upper().replace(' ', ''))

def generate_coin_concept(trend, source):
    """Generate complete coin concept"""
    name = generate_coin_name(trend)
    ticker = generate_ticker(name)
    
    descriptions = [
        f"The official memecoin of {trend}! 🚀",
        f"Riding the {trend} wave to the moon! 🌙",
        f"{trend} holders unite! Community-driven token.",
        f"Inspired by {trend}. Fair launch, no presale!",
        f"The {trend} revolution starts here! 💎🙌",
    ]
    
    concept = {
        'trend': trend,
        'source': source,
        'name': name,
        'ticker': ticker,
        'description': random.choice(descriptions),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return concept

# ============ BOT COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    welcome = (
        "🤖 *Trend Monitor & Coin Generator Bot*\n\n"
        "I monitor trending topics from FREE sources and generate memecoin ideas!\n\n"
        "*Commands:*\n"
        "/trends - Show Google/general trends\n"
        "/twitter - Show Twitter/X trending topics\n"
        "/youtube - Show YouTube trending videos\n"
        "/reddit - Show trending Reddit posts\n"
        "/coins - Show trending coins (CoinGecko)\n"
        "/news - Show latest crypto news\n"
        "/all - Show ALL trends from all sources\n"
        "/generate - Generate coin ideas from trends\n"
        "/auto `on/off` - Auto-notify for new trends\n"
        "/refresh - Manually refresh trend data\n"
        "/help - Show this message\n\n"
        "*Data Sources (100% FREE):*\n"
        "📊 Google Trends\n"
        "🐦 Twitter/X (via Nitter)\n"
        "📺 YouTube Trending\n"
        "🔥 Reddit Crypto Subs\n"
        "💎 CoinGecko Trending\n"
        "📰 Crypto News (CoinTelegraph)\n\n"
        "💡 *Tip:* I update all sources every 30 minutes!"
    )
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def show_trends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current trending topics from Google"""
    if not trending_cache['google_trends']:
        await update.message.reply_text("⏳ Fetching trends for the first time...")
        await update_trending_data()
    
    trends = trending_cache['google_trends']
    last_update = trending_cache['last_update']
    
    if not trends:
        await update.message.reply_text("❌ No trends available. Try /refresh")
        return
    
    message = f"📊 *Google Trending Searches*\n"
    message += f"🕐 Updated: {last_update.strftime('%H:%M:%S')}\n\n"
    
    for i, trend in enumerate(trends[:10], 1):
        message += f"{i}. {trend}\n"
    
    message += f"\n💡 Use /generate to create coin ideas!"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_reddit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show trending Reddit posts"""
    if not trending_cache['reddit_trending']:
        await update.message.reply_text("⏳ Fetching Reddit trends...")
        await update_trending_data()
    
    posts = trending_cache['reddit_trending']
    
    if not posts:
        await update.message.reply_text("❌ No Reddit trends available.")
        return
    
    message = f"🔥 *Trending on Crypto Reddit*\n\n"
    
    for i, post in enumerate(posts[:5], 1):
        message += f"{i}. *{post['title'][:60]}...*\n"
        message += f"   ⬆️ {post['score']} | r/{post['subreddit']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show trending coins from CoinGecko"""
    if not trending_cache['coingecko_trending']:
        await update.message.reply_text("⏳ Fetching trending coins...")
        await update_trending_data()
    
    coins = trending_cache['coingecko_trending']
    
    if not coins:
        await update.message.reply_text("❌ No trending coins available.")
        return
    
    message = f"💎 *Trending Coins (CoinGecko)*\n\n"
    
    for i, coin in enumerate(coins[:10], 1):
        message += f"{i}. *{coin['name']}* (${coin['symbol'].upper()})\n"
        message += f"   📊 Rank: #{coin['market_cap_rank']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Twitter/X trending topics"""
    if not trending_cache['twitter_trends']:
        await update.message.reply_text("⏳ Fetching Twitter trends...")
        await update_trending_data()
    
    trends = trending_cache['twitter_trends']
    
    if not trends:
        await update.message.reply_text("❌ Twitter trends unavailable. Try /refresh in a moment.")
        return
    
    message = f"🐦 *Trending on Twitter/X*\n\n"
    
    for i, trend in enumerate(trends[:10], 1):
        message += f"{i}. {trend}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show YouTube trending videos"""
    if not trending_cache['youtube_trending']:
        await update.message.reply_text("⏳ Fetching YouTube trends...")
        await update_trending_data()
    
    trends = trending_cache['youtube_trending']
    
    if not trends:
        await update.message.reply_text("❌ YouTube trends unavailable.")
        return
    
    message = f"📺 *Trending on YouTube*\n\n"
    
    for i, trend in enumerate(trends[:10], 1):
        message += f"{i}. {trend}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show latest crypto news"""
    if not trending_cache['crypto_news']:
        await update.message.reply_text("⏳ Fetching crypto news...")
        await update_trending_data()
    
    news = trending_cache['crypto_news']
    
    if not news:
        await update.message.reply_text("❌ News unavailable.")
        return
    
    message = f"📰 *Latest Crypto News*\n\n"
    
    for i, headline in enumerate(news[:8], 1):
        message += f"{i}. {headline}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_all_trends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all trends from all sources"""
    if not any([trending_cache['google_trends'], trending_cache['reddit_trending'], 
                trending_cache['coingecko_trending'], trending_cache['youtube_trending'],
                trending_cache['twitter_trends'], trending_cache['crypto_news']]):
        await update.message.reply_text("⏳ Fetching ALL trends...")
        await update_trending_data()
    
    message = f"🌐 *ALL TRENDING DATA*\n\n"
    
    if trending_cache['twitter_trends']:
        message += f"🐦 *Twitter:* {', '.join(trending_cache['twitter_trends'][:3])}\n\n"
    
    if trending_cache['youtube_trending']:
        message += f"📺 *YouTube:* {trending_cache['youtube_trending'][0][:50]}...\n\n"
    
    if trending_cache['google_trends']:
        message += f"📊 *Google:* {', '.join(trending_cache['google_trends'][:3])}\n\n"
    
    if trending_cache['reddit_trending']:
        top_reddit = trending_cache['reddit_trending'][0]
        message += f"🔥 *Reddit:* {top_reddit['title'][:50]}... ({top_reddit['score']}↑)\n\n"
    
    if trending_cache['coingecko_trending']:
        coins = trending_cache['coingecko_trending'][:3]
        coin_names = ', '.join([c['name'] for c in coins])
        message += f"💎 *Coins:* {coin_names}\n\n"
    
    if trending_cache['crypto_news']:
        message += f"📰 *News:* {trending_cache['crypto_news'][0][:60]}...\n\n"
    
    message += "Use specific commands for more details!"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def generate_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate coin ideas from current trends"""
    if not any([trending_cache['google_trends'], trending_cache['reddit_trending'],
                trending_cache['youtube_trending'], trending_cache['twitter_trends']]):
        await update.message.reply_text("⏳ Fetching trends first...")
        await update_trending_data()
    
    await update.message.reply_text("🎨 Generating coin ideas from ALL sources...")
    
    concepts = []
    
    # Generate from Twitter
    for trend in trending_cache['twitter_trends'][:2]:
        concepts.append(generate_coin_concept(trend, '🐦 Twitter'))
    
    # Generate from YouTube
    for trend in trending_cache['youtube_trending'][:2]:
        concepts.append(generate_coin_concept(trend, '📺 YouTube'))
    
    # Generate from Google trends
    for trend in trending_cache['google_trends'][:2]:
        concepts.append(generate_coin_concept(trend, '📊 Google'))
    
    # Generate from Reddit
    for post in trending_cache['reddit_trending'][:1]:
        title_words = post['title'].split()[:3]
        trend_text = ' '.join(title_words)
        concepts.append(generate_coin_concept(trend_text, '🔥 Reddit'))
    
    if not concepts:
        await update.message.reply_text("❌ No trends available to generate ideas.")
        return
    
    message = "🚀 *Generated Coin Concepts*\n\n"
    
    for i, concept in enumerate(concepts[:7], 1):
        message += f"*{i}. {concept['name']}* (${concept['ticker']})\n"
        message += f"📝 {concept['description']}\n"
        message += f"📊 Based on: {concept['trend'][:40]}...\n"
        message += f"🔍 Source: {concept['source']}\n\n"
    
    message += "⚠️ *Next Steps:*\n"
    message += "1. Review the concept\n"
    message += "2. Create logo (Canva/AI)\n"
    message += "3. Deploy on pump.fun\n"
    message += "4. Market on Twitter/Telegram"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def refresh_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually refresh trend data"""
    await update.message.reply_text("🔄 Refreshing all trend data...")
    await update_trending_data()
    await update.message.reply_text("✅ Data refreshed! Use /trends or /generate")

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle auto-notifications"""
    user_id = update.effective_user.id
    
    if len(context.args) != 1 or context.args[0].lower() not in ['on', 'off']:
        await update.message.reply_text(
            "Usage: /auto `on` or /auto `off`",
            parse_mode='Markdown'
        )
        return
    
    status = context.args[0].lower() == 'on'
    
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    
    user_preferences[user_id]['auto_notify'] = status
    
    if status:
        await update.message.reply_text(
            "🔔 Auto-notifications *ENABLED*!\n"
            "I'll notify you when new trending topics appear.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🔕 Auto-notifications *DISABLED*.",
            parse_mode='Markdown'
        )

# ============ BACKGROUND MONITORING ============

async def background_trend_monitor(application: Application):
    """Monitor trends in background and notify users"""
    print("🔍 Background trend monitoring started...")
    
    # Initial update
    await update_trending_data()
    
    while True:
        try:
            await asyncio.sleep(1800)  # 30 minutes
            
            old_trends = set(trending_cache['google_trends'])
            await update_trending_data()
            new_trends = set(trending_cache['google_trends'])
            
            # Find new trends
            fresh_trends = new_trends - old_trends
            
            if fresh_trends:
                # Notify users with auto-notify enabled
                for user_id, prefs in user_preferences.items():
                    if prefs.get('auto_notify', False):
                        message = f"🔥 *New Trending Topics Detected!*\n\n"
                        for trend in list(fresh_trends)[:5]:
                            message += f"• {trend}\n"
                        message += f"\nUse /generate to create coin ideas!"
                        
                        try:
                            await application.bot.send_message(
                                chat_id=user_id,
                                text=message,
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            print(f"Error notifying user {user_id}: {e}")
            
        except Exception as e:
            print(f"Error in trend monitoring: {e}")
            await asyncio.sleep(300)

# ============ MAIN ============

def main():
    if TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ ERROR: Please set TELEGRAM_BOT_TOKEN!")
        return
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("trends", show_trends))
    application.add_handler(CommandHandler("twitter", show_twitter))
    application.add_handler(CommandHandler("youtube", show_youtube))
    application.add_handler(CommandHandler("news", show_news))
    application.add_handler(CommandHandler("all", show_all_trends))
    application.add_handler(CommandHandler("generate", generate_ideas))
    application.add_handler(CommandHandler("reddit", show_reddit))
    application.add_handler(CommandHandler("coins", show_coins))
    application.add_handler(CommandHandler("refresh", refresh_data))
    application.add_handler(CommandHandler("auto", toggle_auto))
    
    # Set bot commands menu
    async def post_init(app: Application):
        commands = [
            BotCommand("trends", "📊 Google/general trends"),
            BotCommand("twitter", "🐦 Twitter trending"),
            BotCommand("youtube", "📺 YouTube trending"),
            BotCommand("all", "🌐 All sources at once"),
            BotCommand("generate", "🎨 Generate coin ideas"),
            BotCommand("reddit", "🔥 Reddit posts"),
            BotCommand("coins", "💎 Trending coins"),
            BotCommand("news", "📰 Crypto news"),
            BotCommand("refresh", "🔄 Refresh data"),
        ]
        await app.bot.set_my_commands(commands)
        
        asyncio.create_task(background_trend_monitor(app))
    
    application.post_init = post_init
    
    print("🤖 Trend Monitor Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
