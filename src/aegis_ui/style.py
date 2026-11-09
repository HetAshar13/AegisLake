"""
AegisLake Mission Control: Executive FinTech Styling & Design Tokens
Provides dark-mode glassmorphic styling, glowing telemetry pills, and compliance certificate styles.
"""

CUSTOM_CSS = """
<style>
    /* Global Page Styling */
    .stApp {
        background-color: #0B0E14;
        color: #E6EDF3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Header Banner Styling */
    .aegis-header {
        background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .aegis-title {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .aegis-subtitle {
        font-size: 14px;
        color: #8B949E;
        margin-top: 4px;
        margin-bottom: 0;
    }

    /* Glassmorphic Card Container */
    .aegis-card {
        background: rgba(22, 27, 34, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .aegis-card:hover {
        border-color: rgba(0, 242, 254, 0.3);
    }

    /* Metric Badges & Tiles */
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #FFFFFF;
        font-feature-settings: "tnum";
    }

    .metric-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8B949E;
        margin-bottom: 6px;
    }

    /* Glowing Status Badges */
    .badge-healthy {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(0, 230, 118, 0.15);
        color: #00E676;
        border: 1px solid rgba(0, 230, 118, 0.4);
        box-shadow: 0 0 12px rgba(0, 230, 118, 0.2);
    }

    .badge-critical {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(255, 75, 75, 0.15);
        color: #FF4B4B;
        border: 1px solid rgba(255, 75, 75, 0.4);
        box-shadow: 0 0 12px rgba(255, 75, 75, 0.2);
    }

    .badge-amber {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(255, 179, 0, 0.15);
        color: #FFB300;
        border: 1px solid rgba(255, 179, 0, 0.4);
        box-shadow: 0 0 12px rgba(255, 179, 0, 0.2);
    }

    .badge-cyan {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(0, 242, 254, 0.15);
        color: #00F2FE;
        border: 1px solid rgba(0, 242, 254, 0.4);
        box-shadow: 0 0 12px rgba(0, 242, 254, 0.2);
    }

    /* Compliance Certificate Card */
    .compliance-seal-box {
        background: linear-gradient(135deg, rgba(16, 37, 28, 0.8) 0%, rgba(13, 23, 20, 0.95) 100%);
        border: 2px solid #00E676;
        border-radius: 16px;
        padding: 24px;
        margin-top: 20px;
        box-shadow: 0 0 30px rgba(0, 230, 118, 0.2);
    }

    .compliance-title {
        font-size: 20px;
        font-weight: 800;
        color: #00E676;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .compliance-meta {
        font-size: 13px;
        color: #A3B8CC;
        line-height: 1.6;
        font-family: monospace;
    }

    /* Pipeline Step Flow */
    .pipeline-step {
        background: rgba(30, 38, 48, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 14px 18px;
        text-align: center;
        margin: 4px;
    }

    .pipeline-step-active {
        background: rgba(0, 242, 254, 0.1);
        border: 1px solid #00F2FE;
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.2);
    }
</style>
"""
