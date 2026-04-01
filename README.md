# Salem 1692: Accusation & Deception - Multiplayer Edition

A digital implementation of the classic social deduction board game "Salem 1692" with full multiplayer support. Players connect over a network to play as either witches or townsfolk in this game of deception, accusation, and strategy.

## 🎮 Game Overview

**Salem 1692** is a social deduction game set during the Salem witch trials. Players are secretly assigned roles as either **Witches** or **Townsfolk**. The Townsfolk must identify and eliminate all Witches, while the Witches secretly work to eliminate enough Townsfolk to seize control.

### Key Features
- **Multiplayer Support**: 4-12 players can join from different computers
- **Real-time Game State**: All players see synchronized game updates
- **Secret Role Assignment**: Players only know their own role
- **Turn-Based Gameplay**: Strategic card draws and accusations
- **Voting System**: Democratic decision-making during accusations
- **Built-in Chat**: Communicate with other players
- **Game History**: All actions logged and visible
- **Automatic IP Detection**: Server displays its local IP address

## 📋 System Requirements

- **Python 3.8 or higher**
- **No external packages required** - Uses only Python standard library
- **Network connection** for multiplayer (same network or internet with port forwarding)

# 🎮 How to Play Multiplayer

---

## 🖥️ On the Host Computer (Server)

1. Run `python server.py`
2. Click **"Start Server"** *(default port: 5555)*
3. Wait for players to connect
4. When **at least 4 players** have connected, click **"Start Game"**

---

## 👤 On Player Computers (Clients)

1. Run `python client.py`
2. Enter the host's IP address *(use `localhost` if playing on the same computer)*
3. Enter your **player name**
4. Click **"Connect"**
5. Wait for the host to start the game
6. When it's your turn, you can **draw cards** or **accuse other players**
7. During the accusation phase, vote **Guilty** or **Not Guilty**

---

## 🌐 Network Requirements

| Requirement | Details |
|---|---|
| Same Network | All players must be on the same network |
| Port Access | Host must allow incoming connections on port `5555` (default) |
| Internet Play | Use **port forwarding** on your router, or a VPN service like **Hamachi** |

![My Screenshot](\Users\CommonerX2\Documents\Year2semester2\Programming in Python\Lec_and_finalprojectreq\S__10412035.jpg)
