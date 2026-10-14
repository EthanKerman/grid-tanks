grid tanks

a tank game that runs in your terminal. shoot the other tank, bullets bounce off walls. first to 5 wins.

you can play 2 players on one keyboard or play against the cpu (easy, normal, or hard).

how to play it

you need python 3. thats it.

git clone https://github.com/EthanKerman/grid-tanks.git
cd grid-tanks
python3 tanks.py

or just download tanks.py and run it.

windows: python on windows doesnt come with curses, so run this once first:

pip install windows-curses

your terminal has to be at least 60x20 or the game will tell you to make it bigger.

controls

          move                diagonals   shoot 
            
 blue    -w a s d              - q e z c  - space 
 red     -i j k l  (or arrows) -  u o m . -  enter 

pressing a direction turns your tank and moves it. press toward a wall to turn without moving
your own bullets can hit you so dont be dumb about bank shots
p pauses, ctrl+c quits

in vs cpu mode you're blue, but you can use either side of the keyboard.

powerups

 S  shield  blocks one hit (your tank turns white) 
 3  triple  shoots 3 bullets at once for a few seconds 
 >  speed  drive way faster for a few seconds 
changing stuff

all the settings are at the top of tanks.py (bullet speed, bounces, points to win, etc). maps are just text in the MAPS list, so you can make your own. they have to be 21 wide and 13 tall, # is a wall, 1 and 2 are where blue and red start.
