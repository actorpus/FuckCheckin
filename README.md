# Fuck the checkin system V2

I, and anyone else who has worked on this project, does not endorse skipping of any university ran even. 
This entire project is purely for educational purposes.

## Setup

The initial setup process will ask for your university username and password, 
you will then need to accept a push request from duo (entering a code is not yet implemented).
The setup will also prompt you for your uni and course, this is for reject (course is "cs")

## Usage

Simply run `sentry.py` at any time before the events you want to skip, and it will do the rest.
If you are planning on sleeping while the code is running it is advised that you leave your systems speakers 
set to maximum volume, if anything goes wrong with the program, or the end of the event is approaching and nobody
has submitted the checkin code to reject, an alarm will play designed to wake you up.

## Note

Be cautious not to share files marked with `.DONOTSHARE.` as they can contain sensitive information (Username, Password, Duo tokens). 
Never share logs with anyone you don't trust as they can be used to extract session tokens

If upgrading to V2 delete both the duo session file and the settings file, V2 uses new architecture for both.
Old devices can be removed at https://duo.york.ac.uk/manage

-----------------

# Thanks to:

### RejectDopamine (CheckOut)
This app uses [reject](https://rejectdopamine.com/) as the backend for sharing / getting codes!
Go show them some love!

-----------------
<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/actorpus/FuckCheckin">FuckCheckin</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://github.com/actorpus/">actorpus</a> is licensed under <a href="http://creativecommons.org/licenses/by-nc-sa/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">CC BY-NC-SA 4.0<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/nc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1"></a></p> 
