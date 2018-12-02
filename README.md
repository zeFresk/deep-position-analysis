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

![equation](http://bit.ly/2Q92dfl)

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

The total amount of nodes calculated is going to be <img src="http://www.sciweavers.org/tex2img.php?eq=%20%5Ctext%7Bnpm%7D%20%5Ctimes%20%5Csum_%7Bk%3D0%7D%5E%7B%5Ctext%7Bdepth%7D-1%7D%20%5Ctext%7Bpv%7D%5E%7Bk%7D&bc=White&fc=Black&im=jpg&fs=12&ff=arev&edit=0" align="center" border="0" alt=" \text{npm} \times \sum_{k=0}^{\text{depth}-1} \text{pv}^{k}" width="146" height="54" />, where *npm* is the number of nodes per move.

The growth is exponential.

Try lowering the nodes count, the pv, or the depth.

### It's a bug I know it
Submit an issue, I will try to fix it :)
