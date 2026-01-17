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

# Store user preferences
user_preferences = {}

# Trending data cache
trending_cache = {
    'google_trends': [],
    'reddit_trending': [],
    'coingecko_trending': [],
    'last_update': None
}

# ============ TREND MONITORING FUNCTIONS ============

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
    print("📊 Updating trending data...")
    
    google_trends = await fetch_google_trends()
    reddit_trends = await fetch_reddit_trending()
    coingecko_trends = await fetch_coingecko_trending()
    
    trending_cache['google_trends'] = google_trends
    trending_cache['reddit_trending'] = reddit_trends
    trending_cache['coingecko_trending'] = coingecko_trends
    trending_cache['last_update'] = datetime.now()
    
    print(f"✅ Updated: {len(google_trends)} Google trends, {len(reddit_trends)} Reddit posts, {len(coingecko_trends)} trending coins")

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
        "/trends - Show current trending topics\n"
        "/generate - Generate coin ideas from trends\n"
        "/reddit - Show trending Reddit posts\n"
        "/coins - Show trending coins (CoinGecko)\n"
        "/auto `on/off` - Auto-notify for new trends\n"
        "/refresh - Manually refresh trend data\n"
        "/help - Show this message\n\n"
        "*Data Sources (100% FREE):*\n"
        "📊 Google Trends\n"
        "🔥 Reddit (r/cryptocurrency, r/solana)\n"
        "💎 CoinGecko Trending\n\n"
        "💡 *Tip:* I update trends every 30 minutes automatically!"
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

async def generate_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate coin ideas from current trends"""
    if not trending_cache['google_trends'] and not trending_cache['reddit_trending']:
        await update.message.reply_text("⏳ Fetching trends first...")
        await update_trending_data()
    
    await update.message.reply_text("🎨 Generating coin ideas...")
    
    concepts = []
    
    # Generate from Google trends
    for trend in trending_cache['google_trends'][:3]:
        concepts.append(generate_coin_concept(trend, 'Google Trends'))
    
    # Generate from Reddit
    for post in trending_cache['reddit_trending'][:2]:
        # Extract key words from title
        title_words = post['title'].split()[:3]
        trend_text = ' '.join(title_words)
        concepts.append(generate_coin_concept(trend_text, 'Reddit'))
    
    if not concepts:
        await update.message.reply_text("❌ No trends available to generate ideas.")
        return
    
    message = "🚀 *Generated Coin Concepts*\n\n"
    
    for i, concept in enumerate(concepts[:5], 1):
        message += f"*{i}. {concept['name']}* (${concept['ticker']})\n"
        message += f"📝 {concept['description']}\n"
        message += f"📊 Based on: {concept['trend']}\n"
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
    application.add_handler(CommandHandler("generate", generate_ideas))
    application.add_handler(CommandHandler("reddit", show_reddit))
    application.add_handler(CommandHandler("coins", show_coins))
    application.add_handler(CommandHandler("refresh", refresh_data))
    application.add_handler(CommandHandler("auto", toggle_auto))
    
    # Set bot commands menu
    async def post_init(app: Application):
        commands = [
            BotCommand("trends", "📊 Show trending topics"),
            BotCommand("generate", "🎨 Generate coin ideas"),
            BotCommand("reddit", "🔥 Trending Reddit posts"),
            BotCommand("coins", "💎 Trending coins"),
            BotCommand("auto", "🔔 Toggle auto-notifications"),
            BotCommand("refresh", "🔄 Refresh data"),
            BotCommand("help", "❓ Help"),
        ]
        await app.bot.set_my_commands(commands)
        
        asyncio.create_task(background_trend_monitor(app))
    
    application.post_init = post_init
    
    print("🤖 Trend Monitor Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
