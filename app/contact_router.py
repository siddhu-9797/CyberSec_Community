# app/contact_router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr as PydanticEmailStr # Keep Pydantic for request validation
import os
from typing import List
import requests # For making HTTP requests
import traceback
from datetime import datetime # For timestamp

print("--- contact_router.py: Module Top-Level (HTTP API with Enhanced User Confirmation Email) ---")

# --- Environment Variable Loading ---
HTTP_API_KEY = os.getenv("SMTP2GO_HTTP_API_KEY", "api-A9D720BCE0FE4502B0C5C7B946E56B59")
print(f"DEBUG contact_router: Using HTTP_API_KEY: '{'********' if HTTP_API_KEY else 'None'}' (Masked)")

SENDER_EMAIL_STR = os.getenv("MAIL_SENDER_EMAIL", "noreply@gophone.ai")
print(f"DEBUG contact_router: Using SENDER_EMAIL_STR for HTTP API: '{SENDER_EMAIL_STR}'")

INTERNAL_RECIPIENT_EMAILS_STR = os.getenv("MAIL_RECIPIENT_EMAILS", "rohithgummadi3@gmail.com")
print(f"DEBUG contact_router: Raw INTERNAL_RECIPIENT_EMAILS_STR for HTTP API: '{INTERNAL_RECIPIENT_EMAILS_STR}'")


# --- Parse and prepare INTERNAL_RECIPIENT_EMAILS_LIST ---
internal_raw_recipient_list = []
if INTERNAL_RECIPIENT_EMAILS_STR:
    internal_raw_recipient_list = [email.strip() for email in INTERNAL_RECIPIENT_EMAILS_STR.split(',') if email.strip()]
print(f"DEBUG contact_router: Parsed internal_raw_recipient_list: {internal_raw_recipient_list}")

if not internal_raw_recipient_list:
    print("ERROR contact_router: No internal recipients found from env var. Defaulting for HTTP API.")
    internal_raw_recipient_list = ["debug_default_recipient@example.com"]


# --- Check for API Key ---
if not HTTP_API_KEY or (HTTP_API_KEY == "api-A9D720BCE0FE4502B0C5C7B946E56B59" and not os.getenv("SMTP2GO_HTTP_API_KEY")):
     print(f"WARNING contact_router: Using default hardcoded HTTP_API_KEY: {HTTP_API_KEY}. Ensure SMTP2GO_HTTP_API_KEY env var is set for production.")
if not HTTP_API_KEY:
    print("CRITICAL ERROR contact_router: SMTP2GO_HTTP_API_KEY is not set. Email sending will fail.")

# --- APIRouter instance ---
router = APIRouter()
print("DEBUG contact_router: APIRouter instance created.")

# --- Pydantic model for contact form data ---
class ContactForm(BaseModel):
    name: str
    email: PydanticEmailStr
    subject: str
    message: str
print("DEBUG contact_router: ContactForm Pydantic model defined.")


async def send_email_via_smtp2go_http_api(
    api_key: str,
    sender: str,
    recipients: List[str],
    subject: str,
    html_body: str,
    text_body: str,
    reply_to_email: str = None
):
    """Helper function to send an email using SMTP2Go HTTP API."""
    payload = {
        "api_key": api_key,
        "sender": sender,
        "to": recipients,
        "subject": subject,
        "text_body": text_body,
        "html_body": html_body,
    }
    if reply_to_email:
        payload["custom_headers"] = [
            {"header": "Reply-To", "value": reply_to_email}
        ]

    smtp2go_api_url = 'https://api.smtp2go.com/v3/email/send'
    log_payload = payload.copy()
    log_payload['api_key'] = '********'
    print(f"DEBUG send_email_via_smtp2go_http_api: Sending POST to {smtp2go_api_url} with payload: {log_payload}")

    try:
        response = requests.post(smtp2go_api_url, json=payload, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        print(f"DEBUG send_email_via_smtp2go_http_api: SMTP2Go API Response: {response_data}")
        return response_data
    except requests.exceptions.HTTPError as http_err:
        error_content = "Unknown error from email service."
        try:
            error_content_detail = http_err.response.json()
            error_content = error_content_detail.get('error_message', str(error_content_detail))
        except ValueError:
            error_content = http_err.response.text
        print(f"ERROR send_email_via_smtp2go_http_api: HTTPError ({http_err.response.status_code}): {error_content}")
        print(f"Full Traceback for HTTPError:\n{traceback.format_exc()}")
        raise Exception(f"HTTPError from SMTP2Go: {http_err.response.status_code} - {error_content}")
    except requests.exceptions.RequestException as req_err:
        print(f"ERROR send_email_via_smtp2go_http_api: RequestException: {req_err}")
        print(f"Full Traceback for RequestException:\n{traceback.format_exc()}")
        raise Exception(f"Network error contacting SMTP2Go: {req_err}")


@router.post("/send")
async def handle_contact_form_via_http_api(form_data: ContactForm):
    print(f"\n--- contact_router (HTTP API): /send endpoint hit ---")
    print(f"DEBUG contact_router /send: Received form_data: name='{form_data.name}', email='{str(form_data.email)}', subject='{form_data.subject}'")

    if not HTTP_API_KEY:
        raise HTTPException(status_code=503, detail="Email service is currently unavailable (API key missing).")
    if not internal_raw_recipient_list:
        raise HTTPException(status_code=500, detail="Internal server error: Email recipient configuration error.")

    # --- Define Theme Colors (REPLACE WITH YOUR ACTUAL HAKTOPUS THEME HEX CODES) ---
    theme_dark_bg = "#04080F"
    theme_neon_cyan = "#09EEF5"
    theme_neon_green = "#03FC84"
    theme_text_primary = "#EEF4FF"
    theme_text_secondary = "#A3B8CC" # Original secondary, might be too dark for some text
    theme_text_secondary_readable = "#C5D5E5" # A lighter secondary for better readability on card_bg
    theme_card_bg = "#101827"
    theme_border_color = "#1A2333"   # Main border for general elements
    theme_text_tertiary = "#6B7F99"
    theme_accent_bg_darker = "#0A101A" # For email headers/footers
    theme_border_color_subtle = "rgba(255, 255, 255, 0.1)" # For subtle dividers like dashed lines
    theme_accent_bg = "#1A2333" # For subject_recap background (can be same as border or card_bg)
    your_simulation_platform_url = "/" # Or "/simulation", or full URL to your platform

    # --- Prepare data for emails ---
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    current_year = datetime.now().year
    unique_request_id_placeholder = "sim-" + os.urandom(4).hex()

    safe_name = form_data.name
    user_email_str = str(form_data.email)
    safe_subject = form_data.subject
    safe_message = form_data.message.replace(chr(10), "<br>")


    # --- 1. Send Notification Email to Internal Team ---
    internal_subject = f"[EnterTheBreach Contact] {safe_subject}"
    # Using main border color for internal email card, can be adjusted
    internal_html_body = f"""
<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>New Contact Form Submission - Enter The Breach</title>
<style>body{{margin:0;padding:0;background-color:{theme_dark_bg};font-family:'Inter',Arial,sans-serif;color:{theme_text_secondary_readable};-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;}}table{{border-collapse:collapse;}}p{{margin:0 0 1em 0;}}strong{{color:{theme_text_primary};}}a{{color:{theme_neon_green};text-decoration:none;}}.email-wrapper{{width:100%;background-color:{theme_dark_bg};padding:20px 0;}}.email-container{{width:100%;max-width:600px;margin:0 auto;background-color:{theme_card_bg};border-radius:8px;border:1px solid {theme_border_color};overflow:hidden;}}.email-header{{padding:30px 25px 20px 25px;border-bottom:1px solid {theme_border_color};text-align:center;background-color:{theme_accent_bg_darker};}}.email-header h1{{margin:0;color:{theme_neon_cyan};font-family:'Outfit',Arial,sans-serif;font-size:26px;font-weight:700;}}.email-content{{padding:30px 25px;color:{theme_text_secondary_readable};font-size:16px;line-height:1.7;}}.email-content .label{{color:{theme_text_primary};font-weight:bold;}}.email-content .message-block{{margin-top:20px;padding-top:20px;border-top:1px solid {theme_border_color_subtle};}}.email-footer{{padding:20px 25px 30px 25px;text-align:center;border-top:1px solid {theme_border_color};background-color:{theme_accent_bg_darker};}}.email-footer p{{margin:0;color:{theme_text_tertiary};font-size:12px;line-height:1.5;}}@media screen and (max-width:600px){{.email-container{{width:95% !important;padding:0 !important;}}.email-header{{padding:25px 15px 15px 15px !important;}}.email-header h1{{font-size:22px !important;}}.email-content{{padding:25px 15px !important;font-size:15px !important;}}.email-footer{{padding:15px 15px 25px 15px !important;}}}}</style></head>
<body><table class="email-wrapper" width="100%" border="0" cellspacing="0" cellpadding="0"><tr><td align="center">
<table class="email-container" border="0" cellspacing="0" cellpadding="0">
<tr><td class="email-header"><h1>New 'Enter The Breach' Contact</h1></td></tr>
<tr><td class="email-content">
<p>You've received a new message from the website contact form:</p>
<p><span class="label">From:</span> {safe_name}</p>
<p><span class="label">Email:</span> <a href="mailto:{user_email_str}" style="color:{theme_neon_green};text-decoration:none;">{user_email_str}</a></p>
<p><span class="label">Subject:</span> {safe_subject}</p>
<div class="message-block"><p><span class="label">Message:</span></p><p style="white-space:pre-wrap;word-wrap:break-word;">{safe_message}</p></div></td></tr>
<tr><td class="email-footer"><p>This email was sent from the HAKTOPUS 'Enter The Breach' platform.<br>Timestamp: {current_timestamp}</p></td></tr>
</table></td></tr></table></body></html>"""
    internal_text_body = f"New contact form submission:\nName: {safe_name}\nEmail: {user_email_str}\nSubject: {safe_subject}\nMessage:\n{form_data.message}"

    internal_email_sent_successfully = False
    try:
        print("DEBUG contact_router /send: Sending internal notification email...")
        internal_response_data = await send_email_via_smtp2go_http_api(
            api_key=HTTP_API_KEY,
            sender=SENDER_EMAIL_STR,
            recipients=internal_raw_recipient_list,
            subject=internal_subject,
            html_body=internal_html_body,
            text_body=internal_text_body,
            reply_to_email=user_email_str
        )
        if internal_response_data.get('data', {}).get('succeeded', 0) >= 1:
            internal_email_sent_successfully = True
            print("INFO contact_router /send: Internal notification email processed successfully by SMTP2Go.")
        else:
            print(f"WARNING contact_router /send: Internal notification email failed according to SMTP2Go. Response: {internal_response_data}")
    except Exception as e:
        print(f"ERROR contact_router /send: Failed to send internal notification email: {e}")


    # --- 2. Send Confirmation Email to the User ---
    user_subject = "Thank You for Contacting Haktopus (Enter The Breach)"
    user_html_body = f"""
<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Message Received - Enter The Breach | HAKTOPUS</title>
<style>body{{margin:0 !important;padding:0 !important;width:100% !important;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;background-color:{theme_dark_bg};color:{theme_text_secondary};font-family:'Inter',Arial,sans-serif;}}table{{border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;}}img{{border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;}}p{{margin:0 0 1em 0;line-height:1.7;}}a{{color:{theme_neon_green};text-decoration:none;}}strong{{color:{theme_text_primary};}}.email-wrapper{{width:100%;background-color:{theme_dark_bg};padding:20px 10px;}}.email-container{{width:100%;max-width:600px;margin:0 auto;background-color:{theme_card_bg};border-radius:12px;border:1px solid {theme_border_color_subtle};overflow:hidden;}}.email-header{{padding:35px 30px 25px 30px;background-color:{theme_accent_bg_darker};border-bottom:1px solid {theme_border_color};text-align:center;}}.email-header .logo-placeholder{{font-family:'Outfit','JetBrains Mono',monospace;font-size:24px;color:{theme_neon_cyan};font-weight:bold;letter-spacing:1px;margin-bottom:15px;}}.email-header h1{{margin:0;color:{theme_text_primary};font-family:'Outfit',Arial,sans-serif;font-size:28px;font-weight:800;line-height:1.3;}}.email-content{{padding:30px 30px 20px 30px;font-size:16px;}}.email-content p{{color:{theme_text_secondary_readable};margin-bottom:18px;}}.email-content .greeting{{font-size:18px;color:{theme_text_primary};margin-bottom:20px;font-weight:500;}}.email-content .subject-recap{{background-color:{theme_accent_bg};padding:15px 20px;border-radius:6px;margin-bottom:25px;border-left:3px solid {theme_neon_green};}}.email-content .subject-recap p{{margin:0;color:{theme_text_primary};}}.email-content .cta-section{{margin-top:30px;padding-top:25px;border-top:1px dashed {theme_border_color_subtle};text-align:center;}}.email-content .cta-section p{{margin-bottom:15px;font-size:14px;color:{theme_text_secondary};}}.email-content .cta-button{{display:inline-block;background-color:{theme_neon_green};color:{theme_dark_bg} !important;padding:12px 25px;border-radius:6px;font-weight:bold;text-decoration:none;font-size:16px;font-family:'Inter',Arial,sans-serif;}}.email-footer{{padding:25px 30px;text-align:center;background-color:{theme_accent_bg_darker};border-top:1px solid {theme_border_color};}}.email-footer p{{margin:0;color:{theme_text_tertiary};font-size:12px;line-height:1.6;}}@media screen and (max-width:600px){{.email-wrapper{{padding:10px 5px;}}.email-container{{width:98% !important;}}.email-header{{padding:25px 20px 20px 20px;}}.email-header h1{{font-size:24px;}}.email-header .logo-placeholder{{font-size:20px;}}.email-content{{padding:25px 20px;}}.email-content p{{font-size:15px;}}.email-content .greeting{{font-size:17px;}}.email-content .cta-button{{padding:12px 20px;font-size:15px;}}.email-footer{{padding:20px;}}}}</style></head>
<body><table class="email-wrapper" width="100%" border="0" cellspacing="0" cellpadding="0"><tr><td align="center">
<table class="email-container" border="0" cellspacing="0" cellpadding="0">
<tr><td class="email-header"><div class="logo-placeholder">HAKTOPUS</div><h1>Your Transmission is Secured.</h1></td></tr>
<tr><td class="email-content">
<p class="greeting">Greetings, {safe_name},</p>
<p>Confirmation: We've successfully received your inquiry regarding:</p><div class="subject-recap"><p><strong>Subject:</strong> "{safe_subject}"</p></div>
<p>Our operatives are processing your request and will deploy a response within approximately 24-48 standard Galactic hours (business hours, Earth time).</p>
<p>Your engagement with the 'Enter The Breach' simulation matrix is valued. Stand by for further communication.</p>
<div class="cta-section"><p>While you await our response, why not re-enter the simulation or explore new scenarios?</p><a href="https://www.haktopus.com/simulation" class="cta-button" style="color:{theme_dark_bg};">Return to The Breach</a></div></td></tr>
<tr><td class="email-footer">
<p>This automated confirmation was dispatched from the HAKTOPUS Command Center.<br>Reference ID: {unique_request_id_placeholder} | Timestamp: {current_timestamp}</p>
<p style="margin-top:10px;">© {current_year} Haktopus. All Rights Reserved. Do Not Reply Directly to this Automated Message.</p></td></tr>
</table></td></tr></table></body></html>"""
    user_text_body = f"Hi {safe_name},\n\nThank you for contacting Haktopus (Enter The Breach) regarding: \"{safe_subject}\".\n\nWe have received your message and will get back to you as soon as possible.\n\nBest regards,\nThe Haktopus Team"

    user_email_sent_successfully = False
    try:
        print(f"DEBUG contact_router /send: Sending confirmation email to user: {user_email_str}...")
        user_response_data = await send_email_via_smtp2go_http_api(
            api_key=HTTP_API_KEY,
            sender=SENDER_EMAIL_STR,
            recipients=[user_email_str],
            subject=user_subject,
            html_body=user_html_body,
            text_body=user_text_body
        )
        if user_response_data.get('data', {}).get('succeeded', 0) >= 1:
            user_email_sent_successfully = True
            print("INFO contact_router /send: User confirmation email processed successfully by SMTP2Go.")
        else:
            print(f"WARNING contact_router /send: User confirmation email failed according to SMTP2Go. Response: {user_response_data}")
    except Exception as e:
        print(f"ERROR contact_router /send: Failed to send user confirmation email: {e}")

    if internal_email_sent_successfully:
        return {"message": "Thank you for your message! We'll get back to you soon."}
    else:
        raise HTTPException(status_code=500, detail="There was an error processing your request. Please try again later or contact us directly.")

print("--- contact_router.py: Module End (HTTP API with User Confirmation & Themed Emails) ---")