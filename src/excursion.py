"""EXCURSION AND THE LATER FILL — measured per journalled reclaim from its own prints, after the lookback. Read by no rule.

measure(path, rec) -> x, every figure a fraction (0.01 = 1 %):
  mfe / mae              furthest above / below the HONEST entry (the next-print fill) from the fill to the honest exit print
  post_mfe / post_mae    the same over the prints after that exit, to the end of the lookback; post_n counts them
  fill_1s / fill_2s      the first print at least 1 s / 2 s after the reclaim print, over the signal spot (as fill_over_signal)
  net_1s / net_2s        net of a position opened at that print and managed by the frozen manage(); why_1s / why_2s its exit
  lag_1s / lag_2s        net_ks − net_honest: what the honest arm overstates for a taker that late (belief B5)

Timestamps are whole seconds and the feed lags 1-2 s, so the 2 s fill is the nearest thing in the prints to a taker's.
Own impact is not in any of it. A key that could not be measured is absent, never zero.
"""
import rule as R


def measure(path, rec):
    hit = R.detect(path)
    if not hit or path[hit[0]][0] != rec["t_entry_s"]:
        return None                                    # a late print changed the path the record was scored on
    i_e, h1 = hit[0], hit[3]
    t_e, entry = path[i_e][0], path[i_e][1]
    x = {}
    if i_e + 1 < len(path):
        t_f, fill = path[i_e + 1][0], path[i_e + 1][1]
        ex, _why, t_x = R.manage(path, t_f, fill, h1)
        j = next((i for i in range(i_e + 2, len(path)) if path[i][0] == t_x and path[i][1] == ex), i_e + 1)
        held, post = [s for _dt, s, _t in path[i_e + 2:j + 1]], [s for _dt, s, _t in path[j + 1:]]
        x.update({"mfe": float(max(held, default=fill) / fill - 1), "mae": float(min(held, default=fill) / fill - 1), "post_n": len(post)})
        if post:
            x.update({"post_mfe": float(max(post) / fill - 1), "post_mae": float(min(post) / fill - 1)})
        honest = R.net_of(fill, ex)
    for k in (1, 2):
        i = next((i for i in range(i_e + 1, len(path)) if path[i][0] >= t_e + k), None)
        if i is not None:
            late = path[i][1]
            ex, why, _t = R.manage(path, path[i][0], late, h1)
            net = R.net_of(late, ex)
            x.update({f"fill_{k}s": float(late / entry - 1), f"net_{k}s": float(net), f"why_{k}s": why, f"lag_{k}s": float(net - honest)})
    return x
