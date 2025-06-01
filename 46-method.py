import argparse
from decimal import Decimal
import enum
import re
from typing import Any


class Fatal(Exception):
    pass

class SingleParamResult(int, enum.ReprEnum):
    FoundSingle = enum.auto()
    FoundMultiple = enum.auto()
    FoundNone = enum.auto()

def single_param(**kwargs) -> tuple[SingleParamResult, tuple[str, Any] | dict]:
    defined = {}
    for k, v in kwargs.items():
        if v is None:
            continue
        defined[k] = v
    match len(defined):
        case 0:
            return SingleParamResult.FoundNone, defined
        case 1:
            return SingleParamResult.FoundSingle, list(defined.items())[0]
        case _:
            return SingleParamResult.FoundMultiple, defined

def cli_main():
    argp = argparse.ArgumentParser()
    argp.add_argument("--ratio", type=int,
                      help="Coffee to water ratio as denominator (default 15 -> 1:15)")
    argp.add_argument("--coffee-g", "-C", type=Decimal,
                      help="Amount of coffee in grams")
    argp.add_argument("--water-g", "-W", type=Decimal,
                      help="Amount of water in grams")
    argp.add_argument("--ratio-override", action="store_true",
                      help="Override ration when both coffee and water amounts are specified")
    argp.add_argument("--pour-time", "-P", type=int, required=True,
                      help="seconds for one pour (depends on grind)")
    argp.add_argument("--ratio40", "-r", type=Decimal,
                      help="Acidity/sweetness ratio for 40% stage pours as decimal")
    argp.add_argument("--ratio40-raw", "-R", type=str,
                      help="--ratio40, but as grams: <1st pour grams>/?|?/<2nd port grams>")
    argp.add_argument("--pours60", "-p", type=int,
                      help="Pours count for 60% stage")
    args = argp.parse_args()

    # pour #1: Acidity
    # pour #2: Sugars
    # pour #N [3,5]: Body/strength

    def _round(d: int|Decimal):
        return round(Decimal(d), 1)

    ratio = 15 if (r := args.ratio) is None else r
    pours60 = 3 if (r := args.pours60) is None else r
    pour_time = args.pour_time

    match single_param(ratio=args.ratio40, raw=args.ratio40_raw):
        case SingleParamResult.FoundSingle, value:
            ratio40_arg = value
        case SingleParamResult.FoundMultiple, _:
            raise Fatal("Should specify either -r or -R")
        case SingleParamResult.FoundNone, _:
            ratio40_arg = "ratio", Decimal("0.5")

    if pours60 > 3:
        raise Fatal("Should not be more than 3 pours in 60% stage")
    if pours60 < 1:
        raise Fatal("Should at least be 1 pour in 60% stage")

    match single_param(coffee=args.coffee_g, water=args.water_g):
        case SingleParamResult.FoundMultiple, _:
            if not args.ratio_override:
                raise Fatal("Can't set both coffee and water unless override")
            raise NotImplemented
        case SingleParamResult.FoundSingle, ("coffee", value):
            args.water_g = _round(value * ratio)
        case SingleParamResult.FoundSingle, ("water", value):
            args.coffee_g = _round(value / ratio)
        case _:
            raise Fatal("Should specify amount")

    total_acc = 0
    def print_row(i, to_pour, *, replace_text=None, no_pour_num=False):
        nonlocal total_acc
        total_acc = _round(total_acc + to_pour)
        sec = i * pour_time
        time_s = f"{sec // 60}:{sec % 60:02}"
        prefix = f"#{'-' if no_pour_num else i+1} |{time_s}|"
        if replace_text is None:
            print(f"{prefix} {total_acc: 4}g (+{to_pour}g)")
        else:
            print(f"{prefix} {replace_text}")

    stage40_water = args.water_g * Decimal('0.4')
    stage60_water = args.water_g - stage40_water
    
    def _ratio_raw_delta(g: str) -> Decimal:
        return stage40_water - Decimal(g)

    def _round_ratio40(ratio40_value: Decimal) -> Decimal:
        return round(ratio40_value, 3)

    match ratio40_arg:
        case "ratio", value:
            ratio40 = _round_ratio40(value)
            if not (0 < value < 1):
                raise Fatal("Invalid ratio40", ratio40)
            stage40_pour1 = _round(stage40_water * ratio40)
            stage40_pour2 = _round(stage40_water - stage40_pour1)
        case "raw", value:
            pat_sep = r"/"
            pat_unk = r"[?*]"
            pat_val = r"[\d.]+"
            m = re.match(rf"({pat_val}){pat_sep}{pat_unk}|"
                         rf"{pat_unk}{pat_sep}({pat_val})", value)
            if m is None:
                raise Fatal("Invalid -R syntax")
            elif (g := m[1]) is not None:
                delta = _ratio_raw_delta(g)
                stage40_pour1 = _round(stage40_water - delta)
                ratio40 = _round_ratio40(1 - (delta /stage40_water))
            elif (g := m[2]) is not None:
                delta = _ratio_raw_delta(g)
                stage40_pour1 = _round(delta)
                ratio40 = _round_ratio40(delta / stage40_water)
            else:
                raise ValueError
            if stage40_pour1 >= stage40_water:
                raise Fatal("Invalid -R proportions")
        case _:
            raise ValueError

    stage40_pour2 = _round(stage40_water - stage40_pour1)

    stage60_pourN = _round(stage60_water / pours60)
    stage60_pourL = stage60_water - (stage60_pourN * (pours60 - 1))

    print(f"Coffee    : {args.coffee_g}g")
    print(f"Water (t) : {args.water_g}g")
    print(f"Ratio C/W : 1:{ratio}")
    print(f"Ratio 40% : {ratio40}")
    print(f"Pours 60% : {pours60}")
    print()

    print_row(0, stage40_pour1)
    print_row(1, stage40_pour2)
    i = 0  # fallback for last print row
    base = 2
    for i in range(pours60):
        if i == pours60 - 1:
            tp = stage60_pourL
        else:
            tp = stage60_pourN
        print_row(base + i, tp)
    print_row(base + i + 1, 0, replace_text="REMOVE BREWER", no_pour_num=True)

if __name__ == '__main__':
    cli_main()
