import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
match_events = pd.read_csv(os.path.join("data", "replays", "round1", "match23_events.csv"))
trades = match_events.iloc[np.where(match_events["Operation"] == "Trade")]
scoreboard = pd.read_csv(os.path.join("data", "replays", "round1", "match23_score_board.csv"))
scoreboard_filtered = scoreboard.iloc[np.where(scoreboard["Team"] == "aaathanoscar")]
log_returns = np.log(trades.Price.iloc[1:]/trades.Price.iloc[:-1])
not_nan = np.where(~np.isnan(log_returns))
plt.plot(trades.Time.iloc[1:].iloc[not_nan], log_returns.iloc[not_nan])
plt.plot(scoreboard_filtered.Time, scoreboard_filtered.ProfitOrLoss)
plt.show()