"""Run the MCU gait with funny, synchronized voice commentary powered by Sarvam AI."""
import argparse
import random
import sys
import time
from hexapod import Robot
from sarvam_speaker import SarvamSpeaker, save_api_key

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


DIALOGUES = {
    'spidey': {
        'start': [
            "Six legs primed and servos humming! Clear the floor, humans!",
            "Step aside! Arachnid express coming through!",
            "Centering joints... 3, 2, 1, let's scuttle!",
            "Booting up walking gait! Watch out for the spider!"
        ],
        'quarter': [
            "Pumping twelve volts through my wires, baby!",
            "Look at that tripod gait! Pure mechanical elegance."
        ],
        'midway': [
            "Halfway there! Why does every hallway feel so long to a hexapod?!",
            "Whew, someone please tell me why I keep drifting slightly to the right!",
            "Leg day is rough when you have three pairs of them!",
            "Midpoint reached! Still upright and undefeated."
        ],
        'near_finish': [
            "Approaching destination! Preparing to engage braking thrusters.",
            "Almost there, don't trip me now!",
            "Final stretch! Coasting into the landing zone."
        ],
        'done': [
            "Mission accomplished! That's one small step for a spider.",
            "Parked and powered down! Time for a spider coffee break.",
            "All servos relaxing. Please don't step on me!",
            "Goal reached! Who's a good hexapod? I am."
        ]
    },
    'desi': {
        'start': [
            "Arre bhai bhai bhai! Spidey aa gaya, raasta saaf karo!",
            "Chalo shuru karte hain! 6 taangein full power mein!",
            "Arey hatto saamne se, robot spider nikal raha hai!"
        ],
        'quarter': [
            "Full speed chal raha hai bhai, clutch chhod diya hai!",
            "Waah! Kya mast chal raha hoon main!"
        ],
        'midway': [
            "Aadha raasta paar! Par ye robot hamesha right kyun ghoomta hai?!",
            "Arre baap re, 6 taangon ki cardio bohot thaka deti hai!",
            "Bohot chal liya bhai, abhi thoda aur bacha hai."
        ],
        'near_finish': [
            "Bas pohanchne hi waale hain, brake maarne ki taiyyari karo!",
            "Manzil kareeb hai dosto, dhyan se dekho!"
        ],
        'done': [
            "Safar khatam! Ab chain ki neend lene do mujhe.",
            "Pohanch gaye! Waah kya baat hai, taaliyan bajti rehni chahiye!",
            "Stop lag gaya! Ab battery recharge karne bhejo mujhe."
        ]
    }
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', help='Board address; defaults to locally saved address')
    parser.add_argument('--steps', type=int, default=10, help='Number of cycles (can be >20, auto-batched)')
    parser.add_argument('--speed', type=int, default=100, choices=range(1, 101), help='Gait speed (1-100)')
    parser.add_argument('--persona', choices=['spidey', 'desi'], default='spidey', help='Voice personality')
    parser.add_argument('--api-key', help='Sarvam API key (overrides saved key)')
    parser.add_argument('--set-key', help='Save Sarvam API key to .local/sarvam.json and exit')
    parser.add_argument('--speaker', default='ritu', help='Sarvam voice persona (e.g. ritu, shubh, simran, meera)')
    parser.add_argument('--model', default='bulbul:v4-flash', help='Sarvam TTS model (default: bulbul:v4-flash)')
    parser.add_argument('--lang', default=None, help='Language code (en-IN or hi-IN, auto-selected if omitted)')
    args = parser.parse_args()

    if args.set_key:
        save_api_key(args.set_key)
        print("Sarvam API key saved successfully to .local/sarvam.json!")
        return

    lang = args.lang or ('hi-IN' if args.persona == 'desi' else 'en-IN')

    speaker = SarvamSpeaker(
        api_key=args.api_key,
        lang=lang,
        speaker=args.speaker,
        model=args.model,
        pace=1.15
    )

    pool = DIALOGUES.get(args.persona, DIALOGUES['spidey'])
    chosen_start = random.choice(pool['start'])
    chosen_mid = random.choice(pool['midway'])
    chosen_done = random.choice(pool['done'])
    chosen_near = random.choice(pool['near_finish']) if args.steps >= 10 else None

    total_steps = max(1, args.steps)
    batches = []
    rem = total_steps
    while rem > 0:
        b = min(rem, 20)
        batches.append(b)
        rem -= b

    # Pre-generate / fetch all speech clips before starting motion
    print(f"🎙️ Preparing voice clips for {total_steps} steps (in {len(batches)} batches)...")
    prefetch_list = [chosen_start, chosen_mid, chosen_done]
    if chosen_near:
        prefetch_list.append(chosen_near)
    speaker.prefetch(prefetch_list)
    print("✅ Voice clips ready!")

    robot = Robot(args.host)
    try:
        robot.command('STOP')
        timing = robot.command('TIMING')
        fields = dict(item.split('=', 1) for item in timing.split()[1:])
        move_ms, settle_ms = int(fields['move_ms']), int(fields['settle_ms'])
        period_ms = move_ms + (100 - args.speed) * (max(move_ms, 8000) - move_ms) // 99

        print("Centering joints...")
        for joint in (1, 2, 3):
            robot.command(f'ENABLE {joint}')
            time.sleep(.6)
            robot.command('PING')

        # Trigger start speech as walk begins
        speaker.speak(chosen_start)

        global_step = 0
        mid_step = total_steps // 2
        near_step = max(total_steps - 3, mid_step + 1)
        spoken_mid = False
        spoken_near = False

        for batch_idx, batch_steps in enumerate(batches):
            robot.command('CLEAR')
            robot.command(f'ADD 100 100 {batch_steps} {args.speed}')
            robot.command('RUN')

            deadline = time.monotonic() + batch_steps * 8 * (period_ms + settle_ms) / 1000 + 15
            while time.monotonic() < deadline:
                time.sleep(.4)
                status = robot.command('STATUS')

                # Parse current step number from status
                step_val = 0
                for part in status.split():
                    if part.startswith('step='):
                        try:
                            step_val = int(part.split('=')[1])
                        except ValueError:
                            pass

                curr_total = global_step + step_val
                if not spoken_mid and curr_total >= mid_step:
                    spoken_mid = True
                    speaker.speak(chosen_mid)

                if chosen_near and not spoken_near and curr_total >= near_step:
                    spoken_near = True
                    speaker.speak(chosen_near)

                if 'running=0 ' in status:
                    if 'action=1 ' not in status:
                        raise RuntimeError('Motion stopped before completing the queue')
                    break
            else:
                raise TimeoutError('MCU gait did not finish within bounded duration')

            global_step += batch_steps

        # Finish dialogue
        speaker.speak(chosen_done, block=True)

    finally:
        try:
            robot.command('STOP')
        finally:
            robot.close()


if __name__ == '__main__':
    main()
