#  PyRoblox

**PyRoblox** (`pyrblx`) is an **external tool** made to explore **roblox's process memory** in an attempt to observe how the data is structured and managed in roblox games.
> This tool is not intended for hacking! *(well it kinda is)*

---

## Features
  - Retrieve the **DataModel** and **VisualEngine** from a roblox process
  - Explore almost all of the untouched assets of any roblox game
  - Partially recover content from **LocalScripts** and **ModuleScripts**
  - Search for assets using *name*, *type* and *memory address*
  - *NEW* - See other player's positions through walls!
  - *NEW* - Fling yourself up in the sky!
  - *NEW* - Change your WalkSpeed and JumpPower in-game!
  - *NEW* - Teleport yourself to any position you want!
  - *NEW* - Disable your character's collision/damage from killbricks!
  - ***EVEN NEWER*** - Inject and execute Luau code in-game!

---

## Usage
1) Start roblox and enter any roblox game
2) Run the file "pyrblx/main.py"
3) A window should appear and automatically install all the necessary requirements
4) The actual application will now appear and attempt connection to the roblox process
5) Once the status is green and reads "Connected", you should be able to explore this game's assets using the explorer in the "Instances" tab. Enjoy!

---

## IMPORTANT
I want to give **HUGE** credit to the following repositories that helped me a lot to understand how memory was managed inside the roblox process:
- https://github.com/RajkoRSL/python-external-roblox
- https://github.com/ElCapor/bloxlib
- https://github.com/justDarian/hyperinjector

*Also shoutout to https://github.com/NtReadVirtualMemory for roblox's memory offsets*

---

## NOTES
  - For now only Windows is supported, sorry!
  - THE SEARCH FEATURE IS VERY BUGGY PLS FORGIVE ME!!!!!!!!
