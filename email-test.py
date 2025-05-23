import requests
import random

def send_otp_email():
    recipient_email = 'rcrohith017@gmail.com'
    otp = random.randint(100000, 999999)

    data = {
        'api_key': 'api-A9D720BCE0FE4502B0C5C7B946E56B59',
        'to': [f'Rohith <{recipient_email}>'],
        'sender': 'noreply@gophone.ai',
        'subject': 'Test Email: Your OTP for Password Reset',
        'html_body': f'<p>This is a test email. Here is your OTP for password reset: <b>{otp}</b></p>',
        'text_body': f'This is a test email. Here is your OTP for password reset: {otp}'
    }

    try:
        print("Sending email...")
        response = requests.post('https://api.smtp2go.com/v3/email/send', json=data)
        response_data = response.json()

        if response_data.get('succeeded') == 1:
            print('Email sent successfully:', response_data)
        else:
            print('Failed to send email. Full response:')
            print(response_data)

    except requests.exceptions.RequestException as error:
        print('Error occurred:', error)

send_otp_email()
