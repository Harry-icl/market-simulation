# Copyright 2021 Optiver Asia Pacific Pty. Ltd.
#
# This file is part of Ready Trader Go.
#
#     Ready Trader Go is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     Ready Trader Go is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public
#     License along with Ready Trader Go.  If not, see
#     <https://www.gnu.org/licenses/>.
import asyncio
import itertools
import numpy as np

from typing import List

from ready_trader_go import BaseAutoTrader, Instrument, Lifespan, Side, Action


LOT_SIZE = 10
TICK_SIZE_IN_CENTS = 1
MAPPING = {
    (Action.AA, Action.AA): 0,
    (Action.AA, Action.AB): 1,
    (Action.AA, Action.N): 2,
    (Action.AB, Action.AA): 3,
    (Action.AB, Action.AB): 4,
    (Action.AB, Action.N): 5,
    (Action.N, Action.AA): 6,
    (Action.N, Action.AB): 7,
    (Action.N, Action.N): 8
}

pAA = [0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33]
pAB = [0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33]


class AutoTrader(BaseAutoTrader):
    """Example Auto-trader.

    When it starts this auto-trader places ten-lot bid and ask orders at the
    current best-bid and best-ask prices respectively. Thereafter, if it has
    a long position (it has bought more lots than it has sold) it reduces its
    bid and ask prices. Conversely, if it has a short position (it has sold
    more lots than it has bought) then it increases its bid and ask prices.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, team_name: str, secret: str):
        """Initialise a new instance of the AutoTrader class."""
        super().__init__(loop, team_name, secret)
        self.order_ids = itertools.count(1)
        self.bids = set()
        self.asks = set()
        self.ask_id = self.ask_price = self.bid_id = self.bid_price = self.position = 0
        self.action = None
        self.previous_round = None
        self.midpoint_price = None
        self.previous_mid_bids = 0 # previous bids at S
        self.previous_mid_asks = 0 # previous bids at S
        self.two_wide = False
        self.last_round_game = False

    def on_error_message(self, client_order_id: int, error_message: bytes) -> None:
        """Called when the exchange detects an error.

        If the error pertains to a particular order, then the client_order_id
        will identify that order, otherwise the client_order_id will be zero.
        """
        self.logger.warning("error with order %d: %s", client_order_id, error_message.decode())
        if client_order_id != 0:
            self.on_order_status_message(client_order_id, 0, 0, 0)

    def on_order_book_update_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                                     ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        """Called periodically to report the status of an order book.

        The sequence number can be used to detect missed or out-of-order
        messages. The five best available ask (i.e. sell) and bid (i.e. buy)
        prices are reported along with the volume available at each of those
        price levels.
        """
        self.logger.info("received order book for instrument %d with sequence number %d", instrument,
                         sequence_number)
        if instrument == Instrument.FUTURE:
            self.send_cancel_order(self.bid_id)
            self.bid_id = 0
            self.send_cancel_order(self.ask_id)
            self.ask_id = 0
            if bid_prices[0] == 0 and ask_prices[0] == 0:
                self.two_wide = False

            elif bid_prices[0] + TICK_SIZE_IN_CENTS == ask_prices[0]:
                new_bid_price = bid_prices[0] - TICK_SIZE_IN_CENTS
                new_ask_price = ask_prices[0] + TICK_SIZE_IN_CENTS
                self.two_wide = False

                self.bid_id = next(self.order_ids)
                self.bid_price = new_bid_price
                self.send_insert_order(self.bid_id, Side.BUY, new_bid_price, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.bids.add(self.bid_id)

                self.ask_id = next(self.order_ids)
                self.ask_price = new_ask_price
                self.send_insert_order(self.ask_id, Side.SELL, new_ask_price, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.asks.add(self.ask_id)

            else:
                self.midpoint_price = (bid_prices[0] + ask_prices[0]) // 2
                self.two_wide = True

        else:
            if self.last_round_game:
                if self.midpoint_price in bid_prices:
                    self.previous_mid_bids += bid_volumes[bid_prices.index(self.midpoint_price)]
                if self.midpoint_price in ask_prices:
                    self.previous_mid_asks += ask_volumes[ask_prices.index(self.midpoint_price)]
                
                if self.action == Action.AA:
                    self.previous_mid_asks -= LOT_SIZE
                elif self.action == Action.AB:
                    self.previous_mid_bids -= LOT_SIZE

                if self.previous_mid_bids >= LOT_SIZE and self.previous_mid_asks >= LOT_SIZE:
                    previous_opponent_action = np.random.choice([Action.AA, Action.AB])
                elif self.previous_mid_bids >= LOT_SIZE:
                    previous_opponent_action = Action.AB
                elif self.previous_mid_asks >= LOT_SIZE:
                    previous_opponent_action = Action.AA
                else:
                    previous_opponent_action = Action.N
                
                self.previous_round = MAPPING[self.action, previous_opponent_action]

                self.previous_mid_asks = 0
                self.previous_mid_bids = 0

                self.last_round_game = False

            if self.two_wide:
                pAAi = pAA[self.previous_round] if self.previous_round is not None else 0.33
                pABi = pAB[self.previous_round] if self.previous_round is not None else 0.33
                pNi = 1 - pAAi - pABi
                self.action = np.random.choice([Action.AA, Action.AB, Action.N],
                                               p=[pAAi, pABi, pNi])
                new_bid_price = self.midpoint_price - TICK_SIZE_IN_CENTS
                new_ask_price = self.midpoint_price + TICK_SIZE_IN_CENTS
                if self.action == Action.AA:
                    new_ask_price -= TICK_SIZE_IN_CENTS
                elif self.action == Action.AB:
                    new_bid_price += TICK_SIZE_IN_CENTS

                self.bid_id = next(self.order_ids)
                self.bid_price = new_bid_price
                self.send_insert_order(self.bid_id, Side.BUY, new_bid_price, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.bids.add(self.bid_id)

                self.ask_id = next(self.order_ids)
                self.ask_price = new_ask_price
                self.send_insert_order(self.ask_id, Side.SELL, new_ask_price, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.asks.add(self.ask_id)

                self.last_round_game = True

    def on_order_filled_message(self, client_order_id: int, price: int, volume: int) -> None:
        """Called when when of your orders is filled, partially or fully.

        The price is the price at which the order was (partially) filled,
        which may be better than the order's limit price. The volume is
        the number of lots filled at that price.
        """
        if client_order_id in self.bids:
            self.position += volume
        elif client_order_id in self.asks:
            self.position -= volume

    def on_order_status_message(self, client_order_id: int, fill_volume: int, remaining_volume: int,
                                fees: int) -> None:
        """Called when the status of one of your orders changes.

        The fill_volume is the number of lots already traded, remaining_volume
        is the number of lots yet to be traded and fees is the total fees for
        this order. Remember that you pay fees for being a market taker, but
        you receive fees for being a market maker, so fees can be negative.

        If an order is cancelled its remaining volume will be zero.
        """
        if remaining_volume == 0:
            if client_order_id == self.bid_id:
                self.bid_id = 0
            elif client_order_id == self.ask_id:
                self.ask_id = 0

            # It could be either a bid or an ask
            self.bids.discard(client_order_id)
            self.asks.discard(client_order_id)

    def on_trade_ticks_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                               ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        self.logger.info("received trade ticks for instrument %d with sequence number %d", instrument,
                         sequence_number)
        if self.midpoint_price in bid_prices:
            self.previous_mid_bids += bid_volumes[bid_prices.index(self.midpoint_price)]
            self.previous_mid_asks += bid_volumes[bid_prices.index(self.midpoint_price)]
        if self.midpoint_price in ask_prices:
            self.previous_mid_asks += ask_volumes[ask_prices.index(self.midpoint_price)]
            self.previous_mid_bids += ask_volumes[ask_prices.index(self.midpoint_price)]
