from enum import Enum
from functools import partial
from social_interaction_cloud import BasicSICConnector
import random
from datetime import datetime


class Text(Enum):
    """
     Static contextual text objects which the Nao robot can say.
     """
    PLAY = "Hello, do you want to play a game of rock, paper, scissors?"
    LETS_PLAY = "Let's play!"
    PLAY_AGAIN = "Do you want to play again?"
    RPS = "Rock, paper, scissors!"
    LOST = "Oh no, I lost!"
    WON = "Yay, I won!"
    TIE = "Oh, it's a tie!"
    SORRY = "Sorry, I did not get that. Please repeat."
    ROCK = "I choose rock."
    PAPER = "I choose paper."
    SCISSORS = "I choose scissors."
    OKAY = "Okay."
    I_CHOOSE = "I choose, {choice}!"
    SCORE = "The final score is: {wins} for me, {loses} for you, and {ties}!"
    DID_NOT_GET = "I did not get that. Please repeat!"
    RESET = "I am going to reset the scores!"


class RPS(Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"


class Result(Enum):
    WON = "won"
    TIE = "Tie"
    LOST = "lost"


def clean_context():
    return {
        # whether the user wants to play
        'wanna_play': False,
        # which sign the user chose
        'user_choice': None,
        # which sign the robot chose
        'robot_choice': None,
        # if the current user input is not understood
        "invalid_user_input": False,
        # wins, ties, loses (from a robot's perspective)
        "result": {Result.WON: 0, Result.TIE: 0, Result.LOST: 0},
        # whether we should reset the context
        "reset": False,
        # the number of played games
        "number_of_games": 0,
        # if a win gesture is shown
        'shown_random_gesture_win': False,
        # if a lost gesture is shown
        'shown_random_gesture_lost': False,
        # if the robogod has been shown
        'shown_robogod': False,
        # the number of sequential wins (- represents number of seq. loses)
        "number_of_seq_wins": 0
    }


class AdvancedRockPaperScissors:
    def __init__(self, server_ip):
        self.sic = BasicSICConnector(server_ip, dialogflow_language='en-US',
                                     dialogflow_key_file='rps-key.json',
                                     dialogflow_agent_id='rps-f9kt', sentiment=True)
        self.context = clean_context()

    def say(self, text_option: Text, params: dict = {}) -> None:
        """
        Let the robot say a certain text. Params can be set (params are replaced in text)

        :param text_option: static Text option to say
        :param params: parameters to replace in the text
        """
        text = str(text_option.value)
        for k, v in params.items():
            text = text.replace(k, str(v))
        self.sic.say(text, sync=True)

    def on_left_foot_pressed(self):
        """
        Resets the context.
        """
        print('left foot pressed')
        self.context['reset'] = True

    def run(self) -> None:
        """
        Run the RPS game
        """
        self.sic.start()
        # register listeners for the foot buttons
        self.sic.subscribe_event_listener('LeftBumperPressed', self.on_left_foot_pressed, continuous=True, sync=False)
        self.sic.set_led_color(['RightFootLeds'], ['green'])
        self.sic.set_led_color(['LeftFootLeds'], ['red'])
        self.sic.subscribe_event_listener('RightBumperPressed', partial(self.yes_no_qa, 'wanna_play', {'text': 'yes'}),
                                          sync=True)
        self.sic.set_led_color(['RightFootLeds'], ['off'])
        self.sic.run_loaded_actions(wait_for_any=True)

        # do the welcoming gesture
        self.sic.do_gesture('intro/behavior_1')
        self.sic.set_language('en-US')

        # wanna_play procedure
        def _wanna_play():
            self.sic.set_eye_color('green')
            self.sic.speech_recognition('answer_yesno', 100, partial(self.yes_no_qa, 'wanna_play'))
            # Check if understood, if not: ask again
            if self.context['invalid_user_input']:
                self.say(Text.DID_NOT_GET)
                _wanna_play()

        # Check if the user want to play
        _wanna_play()

        # play procedure
        def _play():
            # check if a contextual reset was requested
            if self.context['reset']:
                self.say(Text.RESET)
                self.context = clean_context()
                self.context['wanna_play'] = True

            # Play if the user wants to play
            if self.context['wanna_play']:
                self.say(Text.LETS_PLAY)

                # choose a gesture
                always_win = False
                self.context['robot_choice'] = random.choice([RPS.ROCK, RPS.PAPER, RPS.SCISSORS])
                print(f"robot chooses {self.context['robot_choice']}")
                choice_lower = self.context['robot_choice'].value.lower()
                self.sic.do_gesture('startgame/behavior_1')

                # user input retrieval procedure
                def _get_user_choice():
                    self.sic.set_eye_color('green')
                    self.sic.speech_recognition('answers', 10, partial(self.rps_qa, 'user_choice'))
                    # If not understood, ask again
                    if self.context['invalid_user_input']:
                        self.say(Text.DID_NOT_GET)
                        _get_user_choice()

                    # Check what the user chose

                _get_user_choice()

                # check if we should call the robogod (robogod always wins)
                if not self.context['shown_robogod'] and self.context['number_of_games'] > 2 and self.context['result'][
                    Result.LOST] > self.context['result'][Result.WON]:
                    self.context['shown_robogod'] = True
                    self.sic.do_gesture('robogod/behavior_1')
                    always_win = True

                # else, perform the attached gesture
                else:
                    self.sic.do_gesture(f'{choice_lower}/behavior_1')

                # Check the result, from the robot's perspective, and announce it
                res = self.det_result() if not always_win else Result.WON
                res_text = Text.WON if res == Result.WON else Text.LOST if res == Result.LOST else Text.TIE
                self.say(res_text)

                # Update the overall result
                self.context['result'][res] += 1
                self.context['number_of_games'] += 1

                # increment/reset the sequential wins/loses counter
                if res == Result.WON:
                    self.context['number_of_seq_wins'] = max(0, self.context['number_of_seq_wins'] + 1)
                elif res == Result.LOST:
                    self.context["number_of_seq_wins"] = min(0, self.context['number_of_seq_wins'] - 1)

                # maybe do a happy/sad move based on how the game is going
                print(f'N_seq_wins:{self.context["number_of_seq_wins"]}')
                if not self.context['shown_random_gesture_win']:
                    if self.context['number_of_seq_wins'] == 2:
                        self.sic.do_gesture('happy/behavior_1')
                        self.context['shown_random_gesture_win'] = True
                if not self.context['shown_random_gesture_lost']:
                    if self.context['number_of_seq_wins'] == -2:
                        self.sic.do_gesture('sad/behavior_1')
                        self.context['shown_random_gesture_lost'] = True

                # ask if the user wants to play again
                self.say(Text.PLAY_AGAIN)
                self.sic.set_eye_color('green')
                self.sic.speech_recognition('answer_yesno', 10, partial(self.yes_no_qa, 'wanna_play'))
                _play()
            else:
                # The user does not want to play anymore, stopping the SIC and announcing the results
                self.say(Text.OKAY)
                n_wins = self.context['result'][Result.WON]
                n_ties = self.context['result'][Result.TIE]
                n_loses = self.context['result'][Result.LOST]
                self.say(Text.SCORE, {'{wins}': f'{n_wins}{"wins" if n_wins != 1 else "win"}',
                                      '{ties}': f'{n_ties}{"ties" if n_ties != 1 else "tie"}',
                                      '{loses}': f'{n_loses}{"wins" if n_loses != 1 else "win"}'})
                self.sic.do_gesture('goodby/behavior_1')

                # dump the result for scientific purposes
                with open(f'results/advanced-{datetime.timestamp(datetime.now())}-results.txt', mode='w') as f:
                    f.write(str(self.context))
                self.sic.stop()
                return

        _play()

    def yes_no_qa(self, ass_var: str, result):
        """
        Checks if yes/no is said and then sets it in the context
        :param ass_var: variable to assign the yes/no answer to
        :param result: dialogflow's result
        """
        print(result)
        self.sic.set_eye_color('white', load=True)
        if result is None or (not ('yes' == result['text'].lower())
                              and not ('no' == result['text'].lower())):
            self.context['invalid_user_input'] = True
            return
        self.context['invalid_user_input'] = False
        result_text = result['text'].lower()
        yes = 'yes' in result_text
        yeah = 'yeah' in result_text
        self.context[ass_var] = yes or yeah

    def rps_qa(self, ass_var: str, result):
        """
        Checks if rock/paper/scissors is said and then sets it in the context
        :param ass_var: variable to assign the rps answer to
        :param result: dialogflow's result
        """
        print(result)
        self.sic.set_eye_color('white', load=True)
        if result is None or (not ('rock' == result['text'].lower())
                              and not ('paper' == result['text'].lower())
                              and not ('scissors' == result['text'].lower())):
            self.context['invalid_user_input'] = True
            return
        self.context['invalid_user_input'] = False
        self.context[ass_var] = RPS[result['text'].upper()]

    def det_result(self) -> Result:
        """
        Determines the RPS result
        :return: Result object.
        """
        uc = self.context['user_choice']
        rc = self.context['robot_choice']
        if uc == RPS.ROCK:
            if rc == RPS.SCISSORS:
                return Result.LOST
            elif rc == RPS.PAPER:
                return Result.WON
            else:
                return Result.TIE
        elif uc == RPS.PAPER:
            if rc == RPS.ROCK:
                return Result.LOST
            elif rc == RPS.SCISSORS:
                return Result.WON
            else:
                return Result.TIE
        else:
            if rc == RPS.ROCK:
                return Result.WON
            elif rc == RPS.PAPER:
                return Result.LOST
            else:
                return Result.TIE


if __name__ == '__main__':
    rps = AdvancedRockPaperScissors('127.0.0.1')
    rps.run()
