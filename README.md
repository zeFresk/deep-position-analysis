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
- Analyse any fen or epd position with **any installed engine**.
- Customizable **depth** (*be carefull it grows exponentially*)
- Customizable number of best moves to explore (**MultiPV**)
- You can choose between exploring each position for X **nodes** or X **seconds**
- Supports engine configuration


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
You only need to know about the command line parameters :
- *--depth* : tree depth **in plies**.
	`--depth=4` will explore position 2 moves deep
- *--pv* : pick the top-*pv* moves from each position.
	Equivalent to **multiPV** in UCI settings
- *-p*/*--engine* : path to engine [**mandatory**]
- *--nodes* : stop exploring **each node** after set amount of nodes
- *--time* : stop exploring **each node** after set amount of time in **seconds**
- *the position file* in epd or fen format

To *edit engine uci config*, edit the .cfg created in the directory after the first use of the said engine.

#### Important
Total number of positions to analyze is given by formula below :

![equation]( data:image/png;base64,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)

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

The total amount of nodes calculated is going to be ![equation2]( data:image/png;base64,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), where *npm* is the number of nodes per move.

The growth is exponential.

Try lowering the nodes count, the pv, or the depth.

### It's a bug I know it
Submit an issue, I will try to fix it :)
