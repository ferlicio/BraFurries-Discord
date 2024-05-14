# BraFurries-Discord

A feature-rich Discord bot designed to enhance your furry community experience.

## Table of content

* ### [**About The Bot**](#about-the-bot)
* [**Requirements**](#requirements)
* [**Getting started**](#getting-started)
* [**Features & Commands**](#features--commands)
    * [VIP Member Customization](#vip-member-customization)
    * [Member Registration & Info](#member-registration-and-info)
    * [Bot Interactions](#bot-interactions)
    * [XP System](#xp-system)
    * [Roleplay Commands](#roleplay-commands)
    * [Moderation Tools](#moderation-tools)
    * [Utility Commands](#utility-commands)
* [**Common errors**](#common-errors)
* [**Contributing**](#contributing)
* [**Author**](#author)
* [**License**](#license)

## About The Bot

BraFurries-Discord is a comprehensive bot packed with features to streamline community management, foster engagement, and create a fun and interactive environment for your furry members. With its intuitive commands and intuitive interface, the bot empowers you to:

* Personalize VIP member experiences with color and icon customization.
* Facilitate member registration and information tracking.
* Organize and manage events with creation, scheduling, approval workflows, and state-based filtering.
* Implement a dynamic XP system to add a gamified layer to your community.
* Enhance roleplay interactions with dedicated commands for actions like bathing, working, dueling, drawing, and writing.
* Maintain order with effective moderation tools like warnings and role management.
* Empower members with helpful utility commands.

**Please Note:** Some commands may require moderator or administrator permissions that need to be set up.

## Requirements

* **Python:** Version 3.9 or higher (check with `python --version` in your terminal) - [Download](https://www.python.org/downloads/)
* **Pip:** Python package manager (usually comes bundled with Python installation) - [More Info](https://pip.pypa.io/en/stable/installation/)

## Getting Started

**1. Installation**

   - Ensure you have Python and Pip installed on your system.
   - Clone this repository using Git:

     ```bash
     git clone https://github.com/ferlicio/BraFurries-Discord.git
     ```

   - Navigate to the project directory:

     ```bash
     cd BraFurries-Discord
     ```

   - Create a virtual environment (recommended for isolation):

     ```bash
     python -m venv venv  # Replace "venv" with your desired virtual environment name
     source venv/bin/activate  # Activate the virtual environment (Linux/macOS)
     venv\Scripts\activate.bat  # Activate the virtual environment (Windows)
     ```

**2. Configuration**

   - Create a file named `.env` in the project root directory. This file will store your Discord bot token.
   - Add a line like `DISCORD_TOKEN=YOUR_BOT_TOKEN` to the `.env` file, replacing `YOUR_BOT_TOKEN` with your actual Discord bot token (obtained from the Discord Developer Portal).
   - **Important:** Keep the `.env` file excluded from version control (e.g., using a `.gitignore` file).

**3. Required Permissions**

   - Enable the `applications.commands` application scope in the `OAuth2` tab of your Discord Developer Portal.
   - Enable the `Server Members Intent` and `Message Content Intent` in the `Bot` tab of your Discord Developer Portal.

**4. Run the Bot**

   - Install project dependencies:

     ```bash
     pip install -r requirements.txt
     ```

   - Start the bot using the appropriate script (check project files for the specific script name):

     ```bash
     python bot.py  # Example script name
     ```


# Features & Commands

> Note: The repository now uses the new Discord slash commands


### **VIP Member Customization**

* `vip-mudar_cor`: Changes the color of a VIP member's customizable role (format: `#000000`).
* `vip-mudar_icone`: Changes the icon of a VIP member's customizable role for a custom emoji the server has.

### **Member Registration & Info**

* `registrar_local`: Registers your location so people may know you.
* `furros_na_area`: Shows members registered on the specified state.
* `registrar_aniversario`: Registers your birthday for birthday announcements.
* `aniversarios`: Shows upcoming birthdays in the server.

### **Bot Interactions**

* `novo_evento`: Creates a new community event.
* `novo_evento_por_usuario`: Allows users to create their own events.
* `eventos`: Lists all upcoming events.
* `eventos_por_estado`: Filters events by their location.
* `evento`: Shows details of a specific event.
* `evento_reagendar`: Reschedules an existing event (staff only).
* `evento_agendar_prox`: Schedules an event for another date (staff only).
* `eventos_pendentes`: Lists all events awaiting approval (moderator/admin command).
* `evento_aprovar`: Approves a pending event (moderator/admin command).
* `evento_add_staff`: Adds staff members to an event (organizer command).

### **Bot Interactions**

* `{bot_name}_diz`: Makes the bot say something in the specified channel.
* `{bot_name}_status`: Change the bot current status (Playing, Listening, etc.).

### **XP System**

* `xp`: Shows your or someone else current XP balance.
* `xp_ranking`: Shows the top members ranked by XP.
* `xp_resetar`: Resets a member XP (use with caution!).
* `xp_resetar_todos`: Resets everyone's XP (admin command, use with caution!).
* `xp_adicionar`: Adds XP to a user (moderator/admin command).
* `xp_remover`: Removes XP from a user (moderator/admin command).

### **Roleplay Commands**

* `rp_banho`: Have a bath.
* `rp_trabalhar`: Simulates working and earning in-game currency.
* `rp_duelo`: Initiates a roleplay duel with another user.
* `rp_desenhar`: Starts a roleplay drawing session.
* `rp_escrever`: Initiates a roleplay writing session.

### **Moderation Tools**

* `perfil`: Shows a user's profile information.
* `warn`: Issues a warning to a user.
* `portaria_cargos`: Gives the permission to a user get his roles in Portaria.
* `portaria_aprovar`: Approves user that already got their roles in Portaria.

### **Utility Commands**

* `call_titio`: Sends a ping to "Titio", the bot creator (for help or support).
* `temp_role`: Grants a temporary role to a user (duration and role specifications needed).

## Common Errors

Here are some common errors and solutions:

* **Dependencies aren't up to date:** Regularly update packages using `pip install -r requirements.txt`.

## Contributing

We welcome contributions to improve BraFurries Discord Bot! Please see the CONTRIBUTING.md file for guidelines.

## Author

[Fernando FR](https://github.com/ferlicio)

<!-- ## Support me

<a href="https://www.buymeacoffee.com/" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a> -->

## License

This project is licensed under the ***Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License*** - see the [LICENSE.md](LICENSE) file for details
