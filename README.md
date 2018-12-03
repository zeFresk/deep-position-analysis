Deep Position Analysis or DPA
====

Introduction
------------
When practicing openings I thought it would be cool to be able to generate a tree consisting of best moves from any given positions.

And doing that recursively would allow a deeper analysis.

I searched a bit and only found DeA from Fritz which sadly wasn't free. I didn't find any open source alternative.

And so I created my own script which allows you to do exactly that !

Overview
-----------------
- Analyze any fen or epd position with **any installed engine**.
- Analyze **pgn files**, analysis will start at the last position from main line.
- Customizable **depth** (*be carefull it grows exponentially*)
- Customizable number of best moves to explore (**MultiPV**)
- You can choose between exploring each position for X **nodes** or X **seconds**
- Supports engine configuration
- Supports multiple games/positions per file
- Supports multiple files


How to install
--------------
It's really easy : just download the .py and it's dependencies

### Install dependencies
> pip install python-chess

### Clone repository
> git clone XXX

How to use
----------
### Basics
It's easy, you only need to know about the command line parameters needed :
- *--depth* : tree depth **in plies**.
	`--depth=4` will explore position 2 moves deep
- *--pv* : pick the top-*pv* moves from each position.
	Equivalent to **multiPV** in UCI settings
- *-p*/*--engine* : path to engine [**mandatory**]
- *--nodes* : stop exploring **each node** after set amount of nodes
- *--time* : stop exploring **each node** after set amount of time in **seconds**
- *--no-appending* : **do not append** foreshadowed continuation to last nodes. *Off* by default.
- *a file* in epd or fen format **OR** a *pgn* (the analysis will start from the last node of the mainline)

To *edit engine uci config*, edit the .cfg created in the directory after the first use of the said engine.

#### About PGN
If a pgn is feed to the script the output pgn file will contain all the content from the original file.

The analysis (starting from the last node of the main line) will be **appended at the end**.

#### Important
Total number of positions to analyze is given by formula below :

![equation](https://i.imgur.com/abUhhwE.png)

The **growth is exponential** with depth so take care

### Example
> python3 dpa.py -p "C:/Engines/stockfish 10/stockfish_10_x64.exe" --pv=2 --depth 3 --nodes 1000000 sicilian.epd

Will generate a .pgn of 7 nodes where each node will be the best move selected after 1M nodes by stockfish 10.

### Advanced
For more commands use `--help`

It is possible to process multiple fen at once by passing multiple files or by appending each fen to one file (*one position per line*) or both.

You can export the raw tree using `--tree` if you want to process it.

I found a bug
-------------
### Are you using python 2 ?
**Then use python 3 and don't forget the dependancies.**

### It's taking too long !
Sadly you have to blame the maths.

The total amount of nodes calculated is going to be ![equation2](https://i.imgur.com/by3dVO0.png), where *npm* is the number of nodes per move.

The growth is exponential so try lowering the nodes count, the pv, or the depth.

### It's a bug I know it
Submit an issue, I will try to fix it :)
