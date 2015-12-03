# Usage

## Bot

You might want to talk to bot if you're feeling lonely ;-P

The bot is one of the contacts every user has in its contact list. It offers you a simple way to interact with the server:

| **Command** | **Description** |
| ----------- | --------------- |
| `\prune`    | Wipe all your date we are storing on our server|
| `\help`     | Getting a simple help|
| `\sync`     | Resync your contact list with WhatsApp \\ (Determine which contacts are using WhatsApp)|
| `\lastseen` | Get last online timestamp of your buddies \\ (send to Buddy)|
| `\fortune`  | Get a quote|

<note tip>All commands start with a **back**slash!</note>

## Login

**This is outdated!**

| **User**       | CountryCode + PhoneNumber (eg. 4917634911387)|
| **Password**   | WhatsApp password |
| **Domain**     | *example.org* (see INSTALL.md) |
| **Port**       | 5222 |
| **Alias**      | *not required* |
| **Ressource**  | *not required* |
| **Encryption** | *activate!!!*  |

### Buddies

WhatsApp does not store your contacts on their servers. Thus you need to import your contacts manually with your XMPP Client or use [[.:bot|our bot]] to Import your contacts from Google (preferred).

(In Pidgin: Menu => Buddys => Add Buddy)

Just use the same JID format as for your login:

  CountryCode + PhoneNumber + "@whatsapp.example.org"

### Groups

To chat with groups you need to add them manually to your XMPP client.

To get a list of your WhatsApp groups, you can use the AutoDiscovery function of your WhatsApp client.

(In Pidgin: Menu => Buddys => Join Chat => RoomList)

When asked, use this conference server:

  whatsapp.0l.de
  
### Smileys / Emojis

To be able to see smileys, you will need an [[https://github.com/stv0g/unicode-emoji/raw/master/symbola/Symbola.ttf|Unicode emoji font]].

When using pidgin, you might want to check out my [[https://github.com/stv0g/unicode-emoji|Unicode emoji theme]].
