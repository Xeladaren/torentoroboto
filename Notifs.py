
import discord_webhook
import time

import Print

verbose = False

discord_webhook_url = None

def sendNotif(content, embed=None, always_print=False):
    if verbose or always_print:
        sendDiscordNotif(content, embed=embed)

def sendDiscordNotif(content, embed=None, retryCount=10):

    if discord_webhook_url:

        sendDone = False

        while retryCount > 0:
            try:
                webhook = discord_webhook.DiscordWebhook(url=discord_webhook_url, content=content, rate_limit_retry=True)

                if embed:
                    webhook.add_embed(embed)
                response = webhook.execute()

                if response.ok:
                    break

            except Exception as ex:
                Print.Error("Error to send Discord notif : {}".format(ex))

            time.sleep(1)
            retryCount -= 1

    else:
        Print.Warning("No Discord Webhook")
