#!/usr/bin/env python3
"""Calculate a background-corrected result from two vial result lines."""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from io import StringIO


BACKGROUND_DATA = (
    (477.57, 0.160),
    (413.23, 0.179),
    (357.40, 0.215),
    (318.47, 0.234),
    (300.18, 0.267),
    (286.72, 0.292),
    (273.69, 0.299),
    (261.78, 0.324),
)
BACKGROUND_2S_PERCENT = 5.0


@dataclass(frozen=True)
class Vial:
    sample_number: str
    bq: float
    cpm: float
    two_s_percent: float
    lum: float
    tsie: float
    efficiency: float
    count_time: float
    dpm: float


def parse_vial(line: str) -> Vial:
    """Parse one comma-separated instrument result line."""
    try:
        values = next(csv.reader(StringIO(line)))
    except csv.Error as exc:
        raise ValueError(f"invalid CSV input: {exc}") from exc

    if len(values) != 10:
        raise ValueError(f"expected 10 comma-separated fields, got {len(values)}")

    values = [value.strip() for value in values]
    try:
        return Vial(
            sample_number=values[0],
            bq=float(values[2]),
            cpm=float(values[3]),
            two_s_percent=float(values[4]),
            lum=float(values[5]),
            tsie=float(values[6]),
            efficiency=float(values[7]),
            count_time=float(values[8]),
            dpm=float(values[9]),
        )
    except ValueError as exc:
        raise ValueError(f"non-numeric value in vial line: {exc}") from exc


def interpolate_background(tsie: float) -> float:
    """Interpolate or extrapolate background Bq at the supplied tSIE."""
    if tsie >= BACKGROUND_DATA[0][0]:
        point_hi, point_lo = BACKGROUND_DATA[0:2]
    elif tsie <= BACKGROUND_DATA[-1][0]:
        point_hi, point_lo = BACKGROUND_DATA[-2:]
    else:
        for point_hi, point_lo in zip(BACKGROUND_DATA, BACKGROUND_DATA[1:]):
            if point_hi[0] >= tsie >= point_lo[0]:
                break
        else:
            raise ValueError(f"could not locate background points for tSIE {tsie}")

    tsie_hi, bq_hi = point_hi
    tsie_lo, bq_lo = point_lo
    return (tsie_hi - tsie) * (bq_lo - bq_hi) / (tsie_hi - tsie_lo) + bq_hi


def absolute_error(bq: float, two_s_percent: float) -> float:
    """Convert a displayed percentage (for example, 9.41) to absolute Bq."""
    return (two_s_percent / 100.0) * bq


def calculate_result(vial_a: Vial, vial_b: Vial) -> str:
    background_bq = interpolate_background(vial_b.tsie)

    absolute_a = absolute_error(vial_a.bq, vial_a.two_s_percent)
    absolute_b = absolute_error(vial_b.bq, vial_b.two_s_percent)
    absolute_background = absolute_error(background_bq, BACKGROUND_2S_PERCENT)

    corrected_b_absolute = math.hypot(absolute_b, absolute_background)
    final_bq = round(vial_a.bq + vial_b.bq - background_bq, 3)
    if final_bq <= 0:
        raise ValueError(f"final Bq must be positive, got {final_bq:.6f}")

    final_absolute = math.hypot(corrected_b_absolute, absolute_a)
    final_two_s_percent = final_absolute / final_bq * 100
    final_dpm = final_bq * 60
    final_cpm = vial_a.efficiency * final_dpm / 100

    return ",".join(
        (
            vial_a.sample_number,
            "FINAL",
            f"{final_bq:.3f}",
            f"{final_cpm:.3f}",
            f"{final_two_s_percent:.2f}",
            f"{vial_a.lum:.0f}",
            f"{vial_a.tsie:.2f}",
            f"{vial_a.efficiency:.2f}",
            f"{vial_a.count_time:.0f}",
            f"{final_dpm:.3f}",
        )
    )


def main() -> int:
    print("Enter the vial A line:")
    line_a = input()
    print("Enter the vial B line:")
    line_b = input()

    try:
        result = calculate_result(parse_vial(line_a), parse_vial(line_b))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("S#,SMPL_ID,Bq:1,CPMA,A:2S%,LUM,tSIE,Eff Nuc1 In A,Count Time,DPM1")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
