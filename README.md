# Fuck the checkin system V2

V2 ditches selenium and emulates the entire setup signing and session systems from good old web requests only!
When being run for the first time a duo push will need to be accepted, 
after that the code registers itself as a duo device and can authorise its own signings

Be cautious not to share files marked with `.DONOTSHARE.` as they can contain sensitive information
(Username, Password, Duo tokens)

If upgrading to V2 delete both the duo session file and the settings file, V2 uses new architecture for both.
Old devices can be removed at https://duo.york.ac.uk/manage

### TODO:
- [x] Reimplement session management to not use browser emulation
- [x] Reimplement Duo setup script to not use browser emulation
- [x] Reimplement sentry system to work with new architecture
- [ ] Add optional discord / telegram / whatsapp (?) integration 

-----------------

# Thanks to:

### RejectDopamine (CheckOut)
This app uses [reject](https://rejectdopamine.com/) as the backend for sharing / getting codes!
Go show them some love!

-----------------
<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/actorpus/FuckCheckin">FuckCheckin</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://github.com/actorpus/">actorpus</a> is licensed under <a href="http://creativecommons.org/licenses/by-nc-sa/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">CC BY-NC-SA 4.0<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/nc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1"></a></p> 
