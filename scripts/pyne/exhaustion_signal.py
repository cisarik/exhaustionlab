"""
@pyne
"""

from pynecore import Persistent, Series
from pynecore.lib import close, color, input, plot, script

# NOTE: This is a *PyneCore* indicator (runs bar-by-bar like Pine).
# It mirrors your Exhaustion Signal logic and emits boolean markers via plots.


@script.indicator(title="Exhaustion Signal (PyneCore)", overlay=True)
def main():
    # Inputs
    showLevel1 = input.bool("Show Level 1 Signals", True)
    showLevel2 = input.bool("Show Level 2 Signals", True)
    showLevel3 = input.bool("Show Level 3 Signals", True)

    level1 = 9
    level2 = 12
    level3 = 14

    # Persistent state
    cycle: Persistent[int] = 0
    bull: Persistent[int] = 0
    bear: Persistent[int] = 0

    def reset_and_recheck(_c, _c4):
        newBull = 0
        newBear = 0
        newCycle = 0
        if _c < _c4:
            newBull = 1
            newCycle = 1
        elif _c > _c4:
            newBear = 1
            newCycle = 1
        return newBull, newBear, newCycle

    c = close
    c4 = close[4]
    c3 = close[3]
    c2 = close[2]

    currentBull = bull
    currentBear = bear
    currentCycle = cycle

    if currentCycle < level1:
        if c < c4:
            bull = currentBull + 1
            bear = 0
            cycle = bull
        elif c > c4:
            bear = currentBear + 1
            bull = 0
            cycle = bear
        else:
            rb, rs, rc = reset_and_recheck(c, c4)
            bull, bear, cycle = rb, rs, rc
    else:
        if currentBull > 0:
            if currentBull < level2:
                if c < c3:
                    bull = currentBull + 1
                    cycle = bull
                else:
                    rb, rs, rc = reset_and_recheck(c, c4)
                    bull, bear, cycle = rb, rs, rc
            elif currentBull < level3 - 1:
                if c < c2:
                    bull = currentBull + 1
                    cycle = bull
                else:
                    rb, rs, rc = reset_and_recheck(c, c4)
                    bull, bear, cycle = rb, rs, rc
            elif currentBull == level3 - 1:
                if c < c2:
                    bull = level3
                    cycle = bull
                else:
                    rb, rs, rc = reset_and_recheck(c, c4)
                    bull, bear, cycle = rb, rs, rc
        elif currentBear > 0:
            if currentBear < level2:
                if c > c3:
                    bear = currentBear + 1
                    cycle = bear
                else:
                    rb, rs, rc = reset_and_recheck(c, c4)
                    bear, bull, cycle = rs, rb, rc
            elif currentBear < level3 - 1:
                if c > c2:
                    bear = currentBear + 1
                    cycle = bear
                else:
                    rb, rs, rc = reset_and_recheck(c, c4)
                    bear, bull, cycle = rs, rb, rc
            elif currentBear == level3 - 1:
                if c > c2:
                    bear = level3
                    cycle = bear
                else:
                    rb, rs, rc = reset_and_recheck(c, c4)
                    bear, bull, cycle = rs, rb, rc
        else:
            rb, rs, rc = reset_and_recheck(c, c4)
            bull, bear, cycle = rb, rs, rc

    bull_l1 = showLevel1 and (bull == level1)
    bull_l2 = showLevel2 and (bull == level2)
    bull_l3 = showLevel3 and (bull == level3)

    bear_l1 = showLevel1 and (bear == level1)
    bear_l2 = showLevel2 and (bear == level2)
    bear_l3 = showLevel3 and (bear == level3)

    # Emit as numeric 0/1 for later overlay (PyneCore stores series, GUI will read later)
    plot(bull_l1, "bull_l1", color=color.green)
    plot(bull_l2, "bull_l2", color=color.green)
    plot(bull_l3, "bull_l3", color=color.green)
    plot(bear_l1, "bear_l1", color=color.red)
    plot(bear_l2, "bear_l2", color=color.red)
    plot(bear_l3, "bear_l3", color=color.red)

    if bull == level3 or bear == level3:
        bull = 0
        bear = 0
        cycle = 0
