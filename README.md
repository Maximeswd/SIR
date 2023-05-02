# Rock, Paper, Scissors (the NAO way)

### Play RPS

#### 1. Start all the required services

To start all requirements, first make sure the `docker` [repo](https://bitbucket.org/socialroboticshub/docker.git) is
copied into the root of this repository.
Then, to make your life easier, run (Windows only)

```bash
start .\start_requirements.bat
```

PS. Do not forget to connect to the robot via the `.java` program!

#### 2. Install all gestures on the robot

Make sure to install all required gestures on the corresponding NAO-robot (via Choregraph). See
the `nao-gestures` folder.

#### 3. Play the basic or advanced version

- Basic: `python basic-rps.py`
- Advanced: `python advanced-rps.py`

Enjoy! :)