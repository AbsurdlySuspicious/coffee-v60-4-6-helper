import argparse
from decimal import Decimal


class Fatal(Exception):
    pass

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
    ratio40 = Decimal('0.5') if (r := args.ratio40) is None else round(r, 3)
    pour_time = args.pour_time

    if not (0 < ratio40 < 1):
        raise Fatal("Invalid ratio40", ratio40)
    if pours60 > 3:
        raise Fatal("Should not be more than 3 pours in 60% stage")
    if pours60 < 1:
        raise Fatal("Should at least be 1 pour in 60% stage")

    if args.coffee_g and args.water_g:
        if not args.ratio_override:
            raise Fatal("Can't set both coffee and water unless override")
        raise NotImplemented
    elif args.coffee_g:
        args.water_g = _round(args.coffee_g * ratio)
    elif args.water_g:
        args.coffee_g = _round(args.water_g / ratio)
    else:
        raise Fatal("Should specify amount")

    print(f"Coffee    : {args.coffee_g}g")
    print(f"Water (t) : {args.water_g}g")
    print(f"Ratio C/W : 1:{ratio}")
    print(f"Ratio 40% : {ratio40}")
    print(f"Pours 60% : {pours60}")
    print()

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
    stage40_pour1 = _round(stage40_water * ratio40)
    stage40_pour2 = _round(stage40_water - stage40_pour1)
    stage60_pourN = _round(stage60_water / pours60)
    stage60_pourL = stage60_water - (stage60_pourN * (pours60 - 1))

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
