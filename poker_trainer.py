import streamlit as st
import random
import itertools
import os
import pandas as pd
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlencode

from equity import calculate_equity

# ============================================================
# CONSTANTS
# ============================================================
RANKS = '23456789TJQKA'
SUITS = ['\u2665', '\u2666', '\u2663', '\u2660']
RANK_ORDER = {r: i for i, r in enumerate(RANKS)}

# ============================================================
# HAND RELEVANCE — only hands worth quizzing
# ============================================================
RELEVANT_HANDS = set([
    "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
    "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
    "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s",
    "QJs","QTs","Q9s","Q8s","Q7s","Q6s",
    "JTs","J9s","J8s","J7s",
    "T9s","T8s","T7s",
    "98s","97s","96s",
    "87s","86s",
    "76s","75s",
    "65s","64s",
    "54s",
    "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
    "KQo","KJo","KTo","K9o","K8o","K7o","K6o",
    "QJo","QTo","Q9o","Q8o",
    "JTo","J9o",
    "T9o","T8o",
    "98o",
])

# ============================================================
# SPIN & GO CHARTS (сокращённые для краткости, но полные в оригинале)
# ============================================================
CHARTS = {
    "BU 13-16 BB": {
        "type": "categorical",
        "data": {
            "2x raise / call vs all in / jam vs NAI 3b": ["AKo","AQo","AJo","AKs","AQs","AJs","ATs","QQ","JJ","TT","99","88","77"],
            "2x raise / call vs all in / call vs NAI 3b": ["AA","KK","KQs","KJs","KTs","QJs","A9s","A8s","A7s"],
            "2x raise / fold vs all in / fold vs NAI 3b": ["A7o","A6o","A5o","KJo","KTo","K9o","QJo","QTo","JTo","K9s","K8s","K7s","K6s","K5s","Q9s","Q8s","Q7s","J9s","J8s","T8s","98s","97s","87s"],
            "All in": ["66","55","44","33","22","A6s","A5s","A4s","A3s","A2s","QTs","JTs","T9s","KQo","ATo","A9o","A8o","QTs","JTs"],
            "Fold": "EVERYTHING_ELSE"
        },
        "buttons": ["2x raise / call vs all in / jam vs NAI 3b","2x raise / call vs all in / call vs NAI 3b","2x raise / fold vs all in / fold vs NAI 3b","All in","Fold"]
    },
    "BU 10-13 BB": {
        "type": "categorical",
        "data": {
            "2x raise / call vs all in / jam vs NAI 3b": ["AA","KK","QQ","JJ","TT","99","88","KQs","KJs","AKs","AQs","AJs","ATs","A9s"],
            "2x raise / fold vs all in / fold vs NAI 3b": ["K9o","QTo","JTo","K8s","Q8s","J8s","T8s","98s","K7s"],
            "All in": ["77","66","55","44","33","22","A8s","A7s","A6s","A5s","A4s","A3s","A2s","AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","KQo","KJo","KTo","QJo","KTs","K9s","QJs","JTs","T9s","J9s","Q9s"],
            "Fold": "EVERYTHING_ELSE"
        },
        "buttons": ["2x raise / call vs all in / jam vs NAI 3b","2x raise / fold vs all in / fold vs NAI 3b","All in","Fold"]
    },
    "BU < 10 BB": {
        "type": "numerical",
        "data": {
            "AA":10,"KK":10,"QQ":10,"JJ":10,"TT":10,"99":10,"88":10,"77":10,"66":10,"55":10,"44":10,"33":10,"22":10,
            "AKs":10,"AQs":10,"AJs":10,"ATs":10,"A9s":10,"A8s":10,"A7s":10,"A6s":10,"A5s":10,"A4s":10,"A3s":10,"A2s":10,
            "KQs":10,"KJs":10,"KTs":10,"K9s":10,"K8s":10,"K7s":10,"K6s":9,"K5s":9,"K4s":8,"K3s":7,"K2s":7,
            "QJs":10,"QTs":10,"Q9s":10,"Q8s":10,"Q7s":7,"Q6s":7,"Q5s":5,
            "JTs":10,"J9s":10,"J8s":9,"J7s":7,
            "T9s":10,"T8s":10,"T7s":7,
            "98s":10,"97s":9,
            "87s":10,"86s":8,
            "76s":9,
            "AKo":10,"AQo":10,"AJo":10,"ATo":10,"A9o":10,"A8o":10,"A7o":10,"A6o":10,"A5o":10,"A4o":10,"A3o":10,"A2o":10,
            "KQo":10,"KJo":10,"KTo":10,"K9o":8,"K8o":7,"K7o":6,"K6o":5,"K5o":5,
            "QJo":10,"QTo":9,"Q9o":6,"Q8o":5,
            "JTo":9,"J9o":5,
            "T9o":5,
        },
        "buttons": ["All in","Fold"]
    },
    "SB vs BU MR 13-16 BB": {
        "type": "categorical",
        "data": {
            "Re-Raise 2.5x": ["AA","KK"],
            "All in": ["QQ","JJ","TT","99","88","77","66","55","44","AKo","AQo","AJo","ATo","A9o","KQo","KQs","KJs","AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s"],
            "Call": ["A4s","A3s","A2s","Q9s","QTs","QJs","JTs","J9s","T9s","KTs","K9s","KJo","QJo"]
        },
        "buttons": ["Re-Raise 2.5x","All in","Call","Fold"]
    },
    "SB vs BU MR 10-13 BB": {
        "type": "categorical",
        "data": {
            "Re-Raise 2.5x": ["AA","KK"],
            "All in": ["99","88","77","66","55","44","33","QQ","JJ","TT","AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s","KQs","KJs","KTs","AKo","AQo","AJo","ATo","A9o","A8o","A7o","KQo","KJo","QJs"],
            "Call": ["QTs","JTs"]
        },
        "buttons": ["Re-Raise 2.5x","All in","Call","Fold"]
    },
    "SB vs BU MR < 10 BB": {
        "type": "categorical",
        "data": {
            "All in": ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
                       "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                       "KQs","KJs","KTs","QJs","QTs","JTs",
                       "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o",
                       "KQo","KJo"],
            "Fold": "EVERYTHING_ELSE"
        },
        "buttons": ["All in","Fold"]
    },
    "SB vs BU AI < 25 BB": {
        "type": "numerical",
        "data": {
            "AA": 25, "KK": 25, "QQ": 25, "JJ": 25, "TT": 25, "99": 25, "88": 25, "77": 25, "66": 17, "55": 16, "44": 13, "33": 9, "22": 6,

            "AKs": 25, "AQs": 25, "AJs": 20, "ATs": 16, "A9s": 15, "A8s": 14, "A7s": 13, "A6s": 12, "A5s": 11, "A4s": 10, "A3s": 8, "A2s": 8,
            "KQs": 15, "KJs": 13, "KTs": 12, "K9s": 8,  "K8s": 6,  "K7s": 6,  "K6s": 5,  "K5s": 5,  "K4s": 4,  "K3s": 4,  "K2s": 4,
            "QJs": 12, "QTs": 8,  "Q9s": 6,  "Q8s": 5,  "Q7s": 4,  "Q6s": 3,  "Q5s": 3,  "Q4s": 3,  "Q3s": 2,  "Q2s": 2,
            "JTs": 8,  "J9s": 5,  "J8s": 4,  "J7s": 3,  "J6s": 2,  "J5s": 2,  "J4s": 2,  "J3s": 2,  "J2s": 2,
            "T9s": 5,  "T8s": 4,  "T7s": 3,  "T6s": 2,  "T5s": 2,  "T4s": 2,  "T3s": 2,  "T2s": 2,
            "98s": 4,  "97s": 3,  "96s": 3,  "95s": 2,  "94s": 1,  "93s": 1,  "92s": 1,
            "87s": 3,  "86s": 3,  "85s": 2,  "84s": 2,  "83s": 1,  "82s": 1,
            "76s": 3,  "75s": 2,  "74s": 2,  "73s": 1,  "72s": 1,
            "65s": 3,  "64s": 2,  "63s": 2,  "62s": 1,
            "54s": 2,  "53s": 2,  "52s": 1,
            "43s": 2,  "42s": 1,
            "32s": 1,

            "AKo": 25, "AQo": 20, "AJo": 18, "ATo": 15, "A9o": 13, "A8o": 12, "A7o": 10, "A6o": 8,  "A5o": 8,  "A4o": 7,  "A3o": 6,  "A2o": 6,
            "KQo": 25, "KJo": 11, "KTo": 8,  "K9o": 6,  "K8o": 4,  "K7o": 3,  "K6o": 3,  "K5o": 2,  "K4o": 2,  "K3o": 2,  "K2o": 2,
            "QJo": 12, "QTo": 6,  "Q9o": 4,  "Q8o": 2,  "Q7o": 2,  "Q6o": 2,  "Q5o": 1,  "Q4o": 1,  "Q3o": 1,  "Q2o": 1,
            "JTo": 25, "J9o": 3,  "J8o": 2,  "J7o": 2,  "J6o": 1,  "J5o": 1,  "J4o": 1,  "J3o": 1,  "J2o": 1,
            "T9o": 3,  "T8o": 3,  "T7o": 2,  "T6o": 1,  "T5o": 1,  "T4o": 1,  "T3o": 1,  "T2o": 1,
            "98o": 4,  "97o": 2,  "96o": 1,  "95o": 1,  "94o": 1,  "93o": 1,  "92o": 1,
            "87o": 2,  "86o": 2,  "85o": 1,  "84o": 1,  "83o": 1,  "82o": 1,
            "76o": 2,  "75o": 1,  "74o": 1,  "73o": 1,  "72o": 1,
            "65o": 2,  "64o": 1,  "63o": 1,  "62o": 1,
            "54o": 1,  "53o": 1,  "52o": 1,
            "43o": 1,  "42o": 1,
            "32o": 1
        },
        "buttons": ["Call","Fold"]
    },
    "SB vs BU Limp 13-16 BB": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": ["AA","KK","QQ","JJ","TT","AKs","AQs","AJs","KQs"],
            "All in": ["99","88","77","66","55","44","33","22","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s","AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o","KJs","KTs","K9s","QJs","QTs","KQo","KJo"],
            "Call": ["K8s","K7s","K6s","K5s","K4s","K3s","K2s","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s","JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s","J2s","T9s","T8s","T7s","T6s","T5s","T4s","T3s","T2s","98s","97s","96s","95s","87s","86s","85s","84s","76s","75s","74s","73s","65s","64s","63s","62s","54s","53s","52s","43s","42s","32s","KTo","K9o","K8o","QJo","QTo","Q9o","Q8o","JTo","J9o","J8o","T9o","T8o","98o","87o"],
        },
        "buttons": ["3x raise / call vs all in","All in","Call","Fold"]
    },
    "SB vs BU Limp 10-13 BB": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA", "KK", "QQ"
            ],
            "All in": [
                "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
                "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
                "KQs", "KJs", "KTs", "K9s",
                "QJs", "QTs", "JTs",
                "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
                "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"
            ],
            "Call": [
                "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
                "Q9s", "Q8s", "Q7s", "Q6s", "Q5s", "Q4s", "Q3s", "Q2s",
                "J9s", "J8s", "J7s", "J6s", "J5s", "J4s", "J3s", "J2s",
                "T9s", "T8s", "T7s", "T6s",
                "98s", "97s", "96s",
                "87s", "86s", "85s",
                "76s", "75s", "74s",
                "65s", "64s", "63s",
                "54s", "53s", "52s",
                "43s", "42s",
                "32s",
                "K9o",
                "Q9o",
                "J9o",
                "T9o"
            ]
        },
        "buttons": ["3x raise / call vs all in","All in","Call","Fold"]
    },
    "SB vs BU Limp < 10 BB": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA", "KK"
            ],
            "All in": [
                "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
                "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
                "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
                "QJs", "QTs", "Q9s", "Q8s",
                "JTs", "J9s",
                "T9s",
                "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
                "KQo", "KJo", "KTo", "K9o",
                "QJo", "QTo", "JTo"
            ],
            "Call": [
                "Q7s", "Q6s", "Q5s",
                "J8s", "J7s",
                "T8s", "T7s",
                "98s", "97s",
                "87s", "86s",
                "76s", "75s",
                "65s", "64s",
                "54s"
            ]
        },
        "buttons": ["3x raise / call vs all in","All in","Call","Fold"]
    },
    "SB vs BB 13-16 BB": {
        "type": "categorical",
        "data": {
            "2x raise / call vs rejam / jam vs NAI 3b": [
                "AA", "KK", "QQ", "JJ", "TT", "99", "88",
                "AKs", "AQs", "AJs", "ATs",
                "KQs", "KJs", "KTs", "QJs"
            ],
            "2x raise / fold vs AI / fold vs NAI 3b": [
                "K9s", "K8s", "K7s", "K6s", "K5s",
                "QTs", "Q9s", "Q8s",
                "JTs", "J9s", "J8s",
                "KTo", "K9o", "K8o",
                "QTo", "Q9o", "Q8o",
                "JTo", "J9o", "T9o", "98o"
            ],
            "All in": [
                "77", "66", "55", "44", "33", "22",
                "98s", "97s", "87s", "86s", "76s", "65s",
                "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
                "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
                "KQo", "KJo", "QJo"
            ],
            "Limp / fold vs Iso AI / call vs 3x Iso": [
                "K4s", "K3s", "K2s", "Q7s", "Q6s", "J7s", "T7s", "75s"
            ],
            "Limp / fold vs Iso AI / call vs 2.5x Iso": [
                "Q5s", "Q4s", "Q3s", "J6s","J5s","J4s", "T6s", "T5s", "96s", "95s", "85s", "64s", "54s", "K7o", "K6o", "J8o", "T8o", "87o"
            ],
            "Limp / fold vs Iso AI / fold vs NAI Iso": [
                "J4s","J3s","J2s",
                "T4s","T3s","T2s",
                "94s","93s","92s",
                "84s","83s","82s",
                "74s","73s","72s",
                "63s","62s",
                "53s","52s",
                "43s","42s",
                "32s",
                "K5o", "K4o", "K3o", "K2o",
                "Q7o", "Q6o", "J7o", "T7o", "97o", "86o", "76o"
            ]
        },
        "buttons": ["2x raise / call vs rejam / jam vs NAI 3b","2x raise / fold vs AI / fold vs NAI 3b","All in","Limp / fold vs Iso AI / call vs 3x Iso","Limp / fold vs Iso AI / call vs 2.5x Iso","Limp / fold vs Iso AI / fold vs NAI Iso","Fold"]
    },
    "SB vs BB 10-13 BB": {
        "type": "categorical",
        "data": {
            "2x raise / call vs rejam / jam vs NAI 3b": [
                "AA","KK","QQ","JJ","TT","99","88",
                "AKs","AQs","AJs",
                "KQs","KJs",
                "QJs",
            ],
            "All in": [
                "77","66","55","44","33","22",
                "ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s",
                "JTs","J9s","J8s","J7s",
                "T9s","T8s","T7s",
                "98s","97s","96s",
                "87s","86s","85s",
                "76s","75s",
                "65s",
                "54s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o","K8o","K7o",
                "QJo","QTo","Q9o",
                "JTo","J9o",
                "T9o",
            ],
            
            "Limp / fold vs Iso AI / fold vs NAI Iso": [
                "Q3s", "Q2s", "J6s", "J5s", "J4s", "J3s", "J2s", "T6s", "T5s", "T4s", "95s",
                "64s", "K6o", "K5o", "Q8o", "Q7o", "J8o", "J7o", "T8o", "T7o", "98o", "97o", "87o", "76o"
            ]
        },
        "buttons": ["2x raise / call vs rejam / jam vs NAI 3b","All in","Limp / fold vs Iso AI / fold vs NAI Iso","Fold"]
    },
    "SB vs BB 8-10 BB": {
        "type": "categorical",
        "data": {
            "2x raise / call vs rejam / jam vs NAI 3b": [
                "AA","KK","QQ","JJ","TT","99", "88", "AKs","AQs","AJs", "KQs", "KJs", "QJs"
            ],
            "All in": [
                "77","66","55","44","33","22",
                "ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s",
                "JTs","J9s","J8s","J7s",
                "T9s","T8s","T7s","T6s",
                "98s","97s","96s",
                "87s","86s","85s",
                "76s","75s","74s",
                "65s",
                "54s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o","K8o","K7o",
                "QJo","QTo","Q9o",
                "JTo","J9o",
                "T9o"
            ],
            "Limp / fold vs Iso AI / fold vs NAI Iso": [
                "Q3s", "Q2s", "J6s", "J5s", "J4s", "J3s", "J2s", "T6s", "T5s", "T4s", "95s", "64s", "K6o", "K5o", "Q8o", "Q7o", "J8o", "J7o", "T8o", "T7o", "98o", "97o", "87o", "76o"
            ]
        },
        "buttons": ["2x raise / call vs rejam / jam vs NAI 3b","All in","Limp / fold vs Iso AI / fold vs NAI Iso","Fold"]
    },
    "SB vs BB < 10 BB": {
        "type": "numerical",
        "data": {
            "AA": 10, "KK": 10, "QQ": 10, "JJ": 10, "TT": 10, "99": 10, "88": 10, "77": 10, "66": 10, "55": 10, "44": 10, "33": 10, "22": 10,
            
            "AKs": 10, "AQs": 10, "AJs": 10, "ATs": 10, "A9s": 10, "A8s": 10, "A7s": 10, "A6s": 10, "A5s": 10, "A4s": 10, "A3s": 10, "A2s": 10,
            "KQs": 10, "KJs": 10, "KTs": 10, "K9s": 10, "K8s": 10, "K7s": 10, "K6s": 10, "K5s": 10, "K4s": 10, "K3s": 10, "K2s": 10,
            "QJs": 10, "QTs": 10, "Q9s": 10, "Q8s": 10, "Q7s": 10, "Q6s": 10, "Q5s": 10, "Q4s": 10, "Q3s": 10, "Q2s": 10,
            "JTs": 10, "J9s": 10, "J8s": 10, "J7s": 10, "J6s": 10, "J5s": 10, "J4s": 10, "J3s": 10, "J2s": 8,
            "T9s": 10, "T8s": 10, "T7s": 10, "T6s": 10, "T5s": 10, "T4s": 9, "T3s": 7, "T2s": 6,
            "98s": 10, "97s": 10, "96s": 10, "95s": 10, "94s": 6, "93s": 4, "92s": 3,
            "87s": 10, "86s": 10, "85s": 10, "84s": 10, "83s": 2, "82s": 2,
            "76s": 10, "75s": 10, "74s": 10, "73s": 2, "72s": 2,
            "65s": 10, "64s": 10, "63s": 2, "62s": 2,
            "54s": 10, "53s": 6, "52s": 2,
            "43s": 5, "42s": 1,
            "32s": 1,

            "AKo": 10, "AQo": 10, "AJo": 10, "ATo": 10, "A9o": 10, "A8o": 10, "A7o": 10, "A6o": 10, "A5o": 10, "A4o": 10, "A3o": 10, "A2o": 10,
            "KQo": 10, "KJo": 10, "KTo": 10, "K9o": 10, "K8o": 10, "K7o": 10, "K6o": 10, "K5o": 10, "K4o": 10, "K3o": 10, "K2o": 10,
            "QJo": 10, "QTo": 10, "Q9o": 10, "Q8o": 10, "Q7o": 8, "Q6o": 8, "Q5o": 7, "Q4o": 7, "Q3o": 6, "Q2o": 6,
            "JTo": 10, "J9o": 10, "J8o": 10, "J7o": 7, "J6o": 6, "J5o": 5, "J4o": 5, "J3o": 4, "J2o": 4,
            "T9o": 10, "T8o": 10, "T7o": 8, "T6o": 5, "T5o": 4, "T4o": 4, "T3o": 4, "T2o": 4,
            "98o": 10, "97o": 8, "96o": 5, "95o": 4, "94o": 3, "93o": 3, "92o": 3,
            "87o": 10, "86o": 5, "85o": 3, "84o": 2, "83o": 1, "82o": 1,
            "76o": 7, "75o": 2, "74o": 2, "73o": 1, "72o": 1,
            "65o": 2, "64o": 2, "63o": 1, "62o": 1,
            "54o": 2, "53o": 1, "52o": 1,
            "43o": 1, "42o": 1,
            "32o": 1
        },
        "buttons": ["All in","Fold"]
    },
    "BB vs BU MR 13-16 BB": {
        "type": "categorical",
        "data": {
            "Re-Raise 2.5x": ["AA","KK"],
            "All in": ["88","77","66","55","44", "QQ", "JJ", "TT", "99", "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "AKo", "AQo", "AJo", "ATo", "A9o"],
            "Call": [
                "33","22",
                "A7s","A6s","A5s","A4s","A3s","A2s",
                "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s","J2s",
                "T9s","T8s","T7s","T6s","T5s","T4s","T3s","T2s",
                "98s","97s","96s","95s","94s","93s","92s",
                "87s","86s","85s","84s","83s","82s",
                "76s","75s","74s","73s","72s",
                "65s","64s","63s","62s",
                "54s","53s","52s",
                "43s","42s",
                "32s",
                "A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o","K8o","K7o",
                "QJo","QTo","Q9o","Q8o",
                "JTo","J9o","J8o",
                "T9o","T8o",
                "98o",
                "87o"
            ]
        },
        "buttons": ["Re-Raise 2.5x","All in","Call","Fold"]
    },
    "BB vs BU MR 10-13 BB": {
        "type": "categorical",
        "data": {
            "All in": ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
                       "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                       "KQs","KJs",
                       "AKo","AQo","AJo","ATo","A9o",
                       ],
            "Call": [
                "KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s","J2s",
                "T9s","T8s","T7s","T6s","T5s",
                "98s","97s","96s","95s",
                "87s","86s","85s",
                "76s","75s","74s",
                "65s","64s","63s",
                "54s","53s",
                "43s",
                "A7o","A6o","A5o","A4o","A3o","A2o",
                "KJo","KTo","K9o","K8o",
                "QJo","QTo","Q9o",
                "JTo","J9o",
                "T9o",
            ]
        },
        "buttons": ["All in","Call","Fold"]
    },
    "BB vs BU MR < 10 BB": {
        "type": "categorical",
        "data": {
            "All in": ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
                       "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                       "KQs", "AKo", "AQo", "AJo"],
            "Call": [
                "KJs","KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s","J2s",
                "T9s","T8s","T7s","T6s","T5s",
                "98s","97s","96s","95s",
                "87s","86s","85s",
                "76s","75s","74s",
                "65s","64s","63s",
                "54s","53s",
                "43s",
                "ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o","K8o",
                "QJo","QTo","Q9o",
                "JTo","J9o",
                "T9o"
            ]
        },
        "buttons": ["All in","Call","Fold"]
    },
    "BB vs BU AI": {
        "type": "numerical",
        "data": {
            "AA": 25, "KK": 25, "QQ": 25, "JJ": 25, "TT": 25, "99": 25, "88": 25, "77": 25, "66": 25, "55": 18, "44": 14, "33": 12, "22": 8,

            "AKs": 25, "AQs": 25, "AJs": 20, "ATs": 18, "A9s": 16, "A8s": 15, "A7s": 14, "A6s": 13, "A5s": 12, "A4s": 11, "A3s": 11, "A2s": 10,
            "KQs": 16, "KJs": 14, "KTs": 13, "K9s": 10, "K8s": 8, "K7s": 7, "K6s": 7, "K5s": 7, "K4s": 6, "K3s": 6, "K2s": 6,
            "QJs": 13, "QTs": 9, "Q9s": 7, "Q8s": 6, "Q7s": 5, "Q6s": 5, "Q5s": 5, "Q4s": 5, "Q3s": 4, "Q2s": 4,
            "JTs": 9, "J9s": 7, "J8s": 6, "J7s": 5, "J6s": 4, "J5s": 4, "J4s": 4, "J3s": 4, "J2s": 4,
            "T9s": 7, "T8s": 6, "T7s": 5, "T6s": 4, "T5s": 4, "T4s": 3, "T3s": 3, "T2s": 3,
            "98s": 6, "97s": 5, "96s": 4, "95s": 4, "94s": 3, "93s": 3, "92s": 3,
            "87s": 5, "86s": 4, "85s": 4, "84s": 3, "83s": 3, "82s": 3,
            "76s": 5, "75s": 4, "74s": 4, "73s": 3, "72s": 3,
            "65s": 4, "64s": 4, "63s": 3, "62s": 3,
            "54s": 4, "53s": 3, "52s": 3,
            "43s": 3, "42s": 3,
            "32s": 3,

            "AKo": 25, "AQo": 25, "AJo": 18, "ATo": 16, "A9o": 15, "A8o": 14, "A7o": 12, "A6o": 11, "A5o": 10, "A4o": 9, "A3o": 8, "A2o": 8,
            "KQo": 14, "KJo": 13, "KTo": 10, "K9o": 7, "K8o": 6, "K7o": 6, "K6o": 5, "K5o": 5, "K4o": 5, "K3o": 4, "K2o": 4,
            "QJo": 9, "QTo": 7, "Q9o": 6, "Q8o": 5, "Q7o": 4, "Q6o": 4, "Q5o": 3, "Q4o": 3, "Q3o": 3, "Q2o": 3,
            "JTo": 6, "J9o": 5, "J8o": 4, "J7o": 3, "J6o": 3, "J5o": 3, "J4o": 3, "J3o": 3, "J2o": 3,
            "T9o": 5, "T8o": 4, "T7o": 3, "T6o": 3, "T5o": 3, "T4o": 3, "T3o": 3, "T2o": 2,
            "98o": 4, "97o": 3, "96o": 3, "95o": 3, "94o": 3, "93o": 2, "92o": 2,
            "87o": 4, "86o": 3, "85o": 3, "84o": 3, "83o": 2, "82o": 2,
            "76o": 4, "75o": 3, "74o": 3, "73o": 3, "72o": 2,
            "65o": 3, "64o": 3, "63o": 3, "62o": 2,
            "54o": 3, "53o": 3, "52o": 2,
            "43o": 3, "42o": 2,
            "32o": 2
        },
        "buttons": ["Call","Fold"]
    },
    "BB vs BU Limp 13-16 BB": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA", "KK", "QQ", "JJ", "TT", "AKs", "AQs", "KQs"
            ],
            "All in": [
                "99","88","77","66","55","44","33","22",
                "AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KJs","KTs","K9s","K8s",
                "QJs","QTs","Q9s",
                "JTs","J9s",
                "T9s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","Check"]
    },
    "BB vs BU Limp 10-13 BB": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": ["AA","KK","QQ","JJ"],
            "All in": [
                "TT","99","88","77","66","55","44","33","22",
                "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KQs","KJs","KTs","K9s","K8s","K7s",
                "QJs","QTs","Q9s",
                "JTs","J9s",
                "T9s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo",
                "QJo",
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","Check"]
    },
    "BB vs BU Limp < 10 BB": {
        "type": "categorical",
        "data": {
            "All in": [
                "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
                "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s","K4s",
                "QJs","QTs","Q9s","Q8s",
                "JTs","J9s",
                "T9s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o",
                "QJo","QTo",
                "JTo",
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["All in","Check"]
    },
    "BB vs 2pp MR 13-16 BB": {
        "type": "categorical",
        "data": {
            "All in": [
                "AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
                "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KQs","KJs",
                "QJs",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o",
                "KQo"
            ],
            "Call": [
                "KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s",
                "T9s","T8s","T7s","T6s",
                "98s","97s","96s",
                "87s","86s","85s",
                "76s","75s","74s",
                "65s","64s","63s",
                "54s","53s","52s",
                "43s","42s",
                "32s",
                "A3o","A2o",
                "KJo","KTo","K9o",
                "QJo","QTo","Q9o",
                "JTo","J9o",
                "T9o"
            ]
        },
        "buttons": ["All in","Call", "Fold"]
    },
    "BB vs 2pp MR 10-13 BB": {
        "type": "categorical",
        "data": {
            "All in": [
                "AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
                "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KQs","KJs",
                "QJs",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o",
                "KQo", "KJo"
            ],
            "Call": [
                "KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "JTs","J9s","J8s","J7s","J6s",
                "T9s","T8s","T7s","T6s",
                "98s","97s","96s",
                "87s","86s","85s",
                "76s","75s","74s",
                "65s","64s",
                "54s",
                "A3o","A2o",
                "KTo","K9o",
                "QJo","QTo","Q9o",
                "JTo","J9o",
                "T9o"
            ]
        },
        "buttons": ["All in","Call", "Fold"]
    },
    "BB vs 2pp MR < 10 BB": {
        "type": "categorical",
        "data": {
            "All in": [
                "AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
                "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KQs","KJs",
                "QJs",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o",
                "KQo", "KJo"
            ],
            "Call": [
                "KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QTs","Q9s","Q8s","Q7s",
                "JTs","J9s","J8s",
                "T9s","T8s",
                "98s","97s",
                "87s","86s",
                "76s",
                "A3o","A2o",
                "KTo",
                "QJo","QTo",
                "JTo"
            ]
        },
        "buttons": ["All in","Call", "Fold"]
    },
    "BB vs 2pp AI": {
        "type": "numerical",
        "data": {
            "AA": 20, "KK": 20, "QQ": 20, "JJ": 20, "TT": 20, "99": 20, "88": 20, "77": 18, "66": 14, "55": 12, "44": 10, "33": 8, "22": 6,

            "AKs": 20, "AQs": 20, "AJs": 16, "ATs": 13, "A9s": 13, "A8s": 9, "A7s": 8, "A6s": 6, "A5s": 6, "A4s": 6, "A3s": 6, "A2s": 6,
            "KQs": 16, "KJs": 14, "KTs": 12, "K9s": 8, "K8s": 6, "K7s": 6, "K6s": 5, "K5s": 5, "K4s": 5, "K3s": 4, "K2s": 4,
            "QJs": 13, "QTs": 12, "Q9s": 9, "Q8s": 6, "Q7s": 5, "Q6s": 5, "Q5s": 4, "Q4s": 4, "Q3s": 4, "Q2s": 4,
            "JTs": 12, "J9s": 9, "J8s": 8, "J7s": 5, "J6s": 4, "J5s": 4, "J4s": 4, "J3s": 4, "J2s": 3,
            "T9s": 10, "T8s": 8, "T7s": 5, "T6s": 4, "T5s": 4, "T4s": 3, "T3s": 3, "T2s": 3,
            "98s": 8, "97s": 6, "96s": 4, "95s": 4, "94s": 3, "93s": 3, "92s": 3,
            "87s": 8, "86s": 6, "85s": 4, "84s": 4, "83s": 3, "82s": 3,
            "76s": 6, "75s": 5, "74s": 4, "73s": 3, "72s": 3,
            "65s": 6, "64s": 4, "63s": 4, "62s": 3,
            "54s": 4, "53s": 4, "52s": 3,
            "43s": 4, "42s": 3,
            "32s": 3,

            "AKo": 20, "AQo": 16, "AJo": 14, "ATo": 13, "A9o": 8, "A8o": 6, "A7o": 6, "A6o": 5, "A5o": 5, "A4o": 4, "A3o": 4, "A2o": 4,
            "KQo": 13, "KJo": 8, "KTo": 6, "K9o": 5, "K8o": 4, "K7o": 4, "K6o": 3, "K5o": 3, "K4o": 3, "K3o": 3, "K2o": 3,
            "QJo": 8, "QTo": 6, "Q9o": 5, "Q8o": 4, "Q7o": 3, "Q6o": 3, "Q5o": 3, "Q4o": 3, "Q3o": 2, "Q2o": 2,
            "JTo": 6, "J9o": 5, "J8o": 4, "J7o": 3, "J6o": 3, "J5o": 3, "J4o": 2, "J3o": 2, "J2o": 2,
            "T9o": 5, "T8o": 4, "T7o": 3, "T6o": 3, "T5o": 2, "T4o": 2, "T3o": 2, "T2o": 2,
            "98o": 4, "97o": 4, "96o": 3, "95o": 2, "94o": 2, "93o": 2, "92o": 2,
            "87o": 4, "86o": 3, "85o": 3, "84o": 2, "83o": 2, "82o": 2,
            "76o": 4, "75o": 3, "74o": 3, "73o": 2, "72o": 2,
            "65o": 4, "64o": 3, "63o": 2, "62o": 2,
            "54o": 3, "53o": 3, "52o": 2,
            "43o": 3, "42o": 2,
            "32o": 2
        },
        "buttons": ["Call","Fold"]
    },
    "BB vs 2pp Limp 13-16 BB": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA", "KK", "QQ", "JJ", "TT", "99", "AKs", "AQs", "AJs", "KQs", "KJs", "QJs"
            ],
            "All in": [
                "88","77","66","55","44","33","22",
                "ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KTs",
                "QJs",
                "JTs",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo",
                "QJo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","Check"]
    },
    "BB vs 2pp Limp 10-13 BB": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA", "KK", "QQ", "JJ", "TT", "AKs", "AQs", "AJs", "KQs", "KJs", "QJs"
            ],
            "All in": [
                "99","88","77","66","55","44","33","22",
                "ATs", "A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KTs", "K9s", "K8s",
                "QJs", "Q9s",
                "JTs", "J9s", "T9s",
                "AKo", "AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo", "KJo", "KTo",
                "QJo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","Check"]
    },
    "BB vs 2pp Limp < 10 BB": {
        "type": "categorical",
        "data": {
            "All in": [
                "99","88","77","66","55","44","33","22","TT","JJ","QQ","KK","AA",
                "AKs", "AQs", "AJs", "ATs", "A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "KTs", "KJs", "KQs", 
                "QJs", "QTs",
                "JTs",
                "AKo", "AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo", "KJo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["All in","Check"]
    },
    "BB vs SB MR 13-16 BB": {
        "type": "categorical",
        "data": {
            "Re-raise 2.5x": [
                "AA","KK","QQ","JJ","TT","AKo", "AKs", "AQs", "AJs"
            ],
            "All in": [
                "99","88","77","66","55","44","33","22",
                "ATs","A9s","A8s","A7s","A6s",
                "AQo","AJo","ATo","A9o","A8o","A7o","A6o"
            ],
            "Fold": [
                "T4o", "T3o", "T2o",
                "94o", "93o", "92o",
                "84o", "83o", "82o",
                "73o", "72o",
                "62o", "52o", "42o", "32o"
            ],
            "Call": "EVERYTHING_ELSE"
        },
        "buttons": ["Re-raise 2.5x", "All in","Call", "Fold"]
    },
    "BB vs SB MR 10-13 BB": {
        "type": "categorical",
        "data": {
            "Re-raise 2.5x": [
                "AA","KK","QQ","JJ","TT","AKo", "AKs", "AQs", "AJs"
            ],
            "All in": [
                "99","88","77","66","55","44","33","22",
                "ATs","A9s","A8s",
                "AQo","AJo","ATo","A9o","A8o","A7o","A6o"
            ],
            "Fold": [
                "T4o", "T3o", "T2o",
                "94o", "93o", "92o",
                "84o", "83o", "82o",
                "73o", "72o",
                "62o", "52o", "42o", "32o"
            ],
            "Call": "EVERYTHING_ELSE"
        },
        "buttons": ["Re-raise 2.5x", "All in","Call", "Fold"]
    },
    "BB vs SB AI": {
        "type": "numerical",
        "data": {
            "AA": 20, "KK": 20, "QQ": 20, "JJ": 20, "TT": 20, "99": 20, "88": 20, "77": 20, "66": 20, "55": 20, "44": 14, "33": 10, "22": 8,

            "AKs": 20, "AQs": 20, "AJs": 20, "ATs": 20, "A9s": 20, "A8s": 20, "A7s": 18, "A6s": 15, "A5s": 15, "A4s": 14, "A3s": 12, "A2s": 12,
            "KQs": 16, "KJs": 15, "KTs": 12, "K9s": 10, "K8s": 9, "K7s": 9, "K6s": 8, "K5s": 7, "K4s": 7, "K3s": 7, "K2s": 7,
            "QJs": 13, "QTs": 12, "Q9s": 9, "Q8s": 8, "Q7s": 7, "Q6s": 7, "Q5s": 6, "Q4s": 6, "Q3s": 6, "Q2s": 5,
            "JTs": 10, "J9s": 9, "J8s": 7, "J7s": 7, "J6s": 6, "J5s": 5, "J4s": 5, "J3s": 4, "J2s": 4,
            "T9s": 9, "T8s": 7, "T7s": 6, "T6s": 4, "T5s": 4, "T4s": 4, "T3s": 4, "T2s": 3,
            "98s": 7, "97s": 6, "96s": 4, "95s": 4, "94s": 3, "93s": 3, "92s": 3,
            "87s": 6, "86s": 4, "85s": 4, "84s": 3, "83s": 3, "82s": 3,
            "76s": 4, "75s": 4, "74s": 3, "73s": 3, "72s": 3,
            "65s": 4, "64s": 3, "63s": 3, "62s": 3,
            "54s": 4, "53s": 3, "52s": 3,
            "43s": 3, "42s": 3,
            "32s": 3,

            "AKo": 20, "AQo": 20, "AJo": 20, "ATo": 20, "A9o": 20, "A8o": 15, "A7o": 14, "A6o": 11, "A5o": 11, "A4o": 11, "A3o": 10, "A2o": 10,
            "KQo": 12, "KJo": 11, "KTo": 10, "K9o": 9, "K8o": 9, "K7o": 8, "K6o": 7, "K5o": 7, "K4o": 6, "K3o": 6, "K2o": 6,
            "QJo": 10, "QTo": 9, "Q9o": 8, "Q8o": 7, "Q7o": 6, "Q6o": 5, "Q5o": 5, "Q4o": 4, "Q3o": 4, "Q2o": 4,
            "JTo": 8, "J9o": 7, "J8o": 6, "J7o": 4, "J6o": 4, "J5o": 4, "J4o": 4, "J3o": 3, "J2o": 3,
            "T9o": 6, "T8o": 4, "T7o": 4, "T6o": 4, "T5o": 4, "T4o": 3, "T3o": 3, "T2o": 3,
            "98o": 4, "97o": 4, "96o": 4, "95o": 3, "94o": 3, "93o": 2, "92o": 2,
            "87o": 4, "86o": 4, "85o": 3, "84o": 3, "83o": 2, "82o": 2,
            "76o": 3, "75o": 3, "74o": 3, "73o": 2, "72o": 2,
            "65o": 3, "64o": 3, "63o": 2, "62o": 2,
            "54o": 3, "53o": 2, "52o": 2,
            "43o": 2, "42o": 2,
            "32o": 2
        },
        "buttons": ["Call","Fold"]
    },
    "BB vs SB Limp 13-16 BB": {
        "type": "categorical",
        "data": {
            "Raise 2.5x / call vs all in": [
                "AA","KK","QQ","JJ","TT","99","88","77","AKs", "AQs", "AJs","ATs","KQs","KJs","KTs","K9s","QJs","QTs","Q9s","JTs","J9s","T9s"
            ],
            "All in": [
                "66","55","44","33","22",
                "A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o"
            ],
            "Raise 2.5x / fold vs all in": [
                "KQo","KJo","KTo","K9o","K8o","QJo","QTo","Q9o","JTo","K8s","K7s","K6s","Q8s","J8s","T8s","98s","87s"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["Raise 2.5x / call vs all in", "Raise 2.5x / fold vs all in", "All in","Check"]
    },
    "BB vs SB Limp 10-13 BB": {
        "type": "categorical",
        "data": {
            "Raise 2.5x / call vs all in": [
                "AA","KK","QQ","JJ","TT","99","88","AKs", "AQs","KQs","KJs","QJs"
            ],
            "All in": [
                "77","66","55","44","33","22",
                "A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s","ATs","AJs",
                "KTs","K9s","K8s", "K7s", "K6s", "K5s",
                "QTs","Q9s", "Q8s",
                "JTs","J9s","T9s", "J8s", "98s", "97s", "87s", "T8s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo", "KJo", "KTo", "QJo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["Raise 2.5x / call vs all in","All in","Check"]
    },
    "BB vs SB Limp < 10 BB": {
        "type": "categorical",
        "data": {
            "Raise 2.5x / call vs all in": [
                "AA","KK","QQ"
            ],
            "All in": [
                "JJ","TT","99","88","AKs", "AQs","KQs","KJs","QJs",
                "77","66","55","44","33","22",
                "A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s","ATs","AJs",
                "KTs","K9s","K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
                "QTs","Q9s", "Q8s", "Q7s",
                "JTs","J9s","T9s", "J8s", "98s", "97s", "87s", "T8s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo", "KJo", "KTo", "QJo", "K9o", "K8o", "Q9o", "JTo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["Raise 2.5x / call vs all in","All in","Check"]
    },
}

# ============================================================
# HU CHARTS (сокращённо, но оригинал содержится)
# ============================================================
HU_CHARTS = {
    "HU SB 20bb+": {
        "type": "categorical",
        "data": {
            "2x raise / call AI / jam vs NAI 3b": [
                "AA","KK","QQ","JJ","TT","99","88",
                "AKs","AQs","AJs","ATs",
                "AKo","AQo","AJo"
            ],
            "2x raise / fold vs AI / fold vs NAI 3b": [
                "A9s","A8s","A7s",
                "KQs","KJs","KTs","K9s","K8s",
                "QJs","QTs","Q9s","Q8s",
                "JTs","J9s",
                "T9s",
                "33", "22",
                "ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o","K8o",
                "QJo","QTo","Q9o",
                "JTo"
            ],
            "Limp / fold vs Iso AI / call vs 3x Iso": [
                "A6s","A5s","A4s","A3s","A2s",
                "K7s","K6s","K5s","K4s","K3s","K2s",
                "Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "J8s","J7s","J6s","J5s","J4s","J3s","J2s",
                "T8s","T7s","T6s","T5s",
                "98s","97s","96s","95s",
                "87s","86s","85s","84s",
                "76s","75s","74s",
                "65s","64s","63s",
                "54s","53s",
                "43s",
                "K7o","K6o",
                "Q8o","Q7o",
                "J9o","J8o","J7o",
                "T9o","T8o","T7o",
                "98o","97o",
                "87o","76o"
            ],
            "All in": ["77","66","55","44"],
            "Limp / fold vs Iso AI / fold vs NAI Iso": "EVERYTHING_ELSE"
        },
        "buttons": ["2x raise / call AI / jam vs NAI 3b","2x raise / fold vs AI / fold vs NAI 3b","Limp / fold vs Iso AI / call vs 3x Iso","Limp / fold vs Iso AI / fold vs NAI Iso","All in","Fold"]
    },
    "HU SB 16-20bb": {
        "type": "categorical",
        "data": {
            "2x raise / call AI / jam vs NAI 3b": [
                "AA","KK","QQ","JJ","TT","99","88",
                "AKs","AQs","AJs","ATs",
                "AKo","AQo","AJo"
            ],
            "2x raise / fold vs AI / fold vs NAI 3b": [
                "A9s","A8s","A7s",
                "KQs","KJs","KTs","K9s","K8s",
                "QJs","QTs","Q9s","Q8s",
                "JTs","J9s",
                "T9s",
                "ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o","K8o",
                "QJo","QTo","Q9o",
                "JTo"
            ],
            "Limp / fold vs Iso AI / call vs 3x Iso": [
                "A6s","A5s","A4s","A3s","A2s",
                "K7s","K6s","K5s","K4s","K3s","K2s",
                "Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "J8s","J7s","J6s","J5s","J4s","J3s","J2s",
                "T8s","T7s","T6s","T5s",
                "98s","97s","96s","95s",
                "87s","86s","85s","84s",
                "76s","75s","74s",
                "65s","64s","63s",
                "54s","53s",
                "43s",
                "K7o","K6o",
                "Q8o","Q7o",
                "J9o","J8o","J7o",
                "T9o","T8o","T7o",
                "98o","97o",
                "87o","76o"
            ],
            "All in": ["77","66","55","44","33","22"],
            "Limp / fold vs Iso AI / fold vs NAI Iso": "EVERYTHING_ELSE"
        },
        "buttons": ["2x raise / call AI / jam vs NAI 3b","2x raise / fold vs AI / fold vs NAI 3b","Limp / fold vs Iso AI / call vs 3x Iso","Limp / fold vs Iso AI / fold vs NAI Iso","All in","Fold"]
    },
    "HU SB 13-16bb": {
        "type": "categorical",
        "data": {
            "2x raise / call AI / jam vs NAI 3b": [
                "AA","KK","QQ","JJ","TT","99",
                "AKs","AQs","AJs","ATs",
                "AKo","AQo","AJo","ATo","KQo",
                "A9s","A8s", 
                "KQs","KJs","KTs"
            ],
            "2x raise / fold vs AI / fold vs NAI 3b": [
                "K9s","K8s",
                "QJs","QTs","Q9s","Q8s",
                "JTs","J9s",
                "T9s",
                "A6o","A5o","A4o","A3o","A2o",
                "KJo","KTo","K9o","K8o",
                "QJo","QTo","Q9o",
                "JTo"
            ],
            "Limp / fold vs Iso AI / call vs 3x Iso": [
                "A7s","A6s","A5s","A4s","A3s","A2s",
                "K7s","K6s","K5s","K4s","K3s","K2s",
                "Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "J8s","J7s","J6s","J5s","J4s","J3s","J2s",
                "T8s","T7s","T6s","T5s",
                "98s","97s","96s","95s",
                "87s","86s","85s","84s",
                "76s","75s","74s",
                "65s","64s","63s",
                "54s","53s",
                "43s",
                "K7o","K6o",
                "Q8o","Q7o",
                "J9o","J8o","J7o",
                "T9o","T8o","T7o",
                "98o","97o",
                "87o","76o"
            ],
            "All in": ["88","77","66","55","44","33","22","A9o","A8o","A7o"],
            "Limp / fold vs Iso AI / fold vs NAI Iso": "EVERYTHING_ELSE"
        },
        "buttons": ["2x raise / call AI / jam vs NAI 3b","2x raise / fold vs AI / fold vs NAI 3b","Limp / fold vs Iso AI / call vs 3x Iso","Limp / fold vs Iso AI / fold vs NAI Iso","All in","Fold"]
    },
    "HU SB 10-13bb": {
        "type": "categorical",
        "data": {
            "2x raise / call AI / jam vs NAI 3b": [
                "AA","KK","QQ","JJ","TT","99",
                "AKs","AQs","AJs","ATs","A9s",
                "KQo","KJo",
                "KQs","KJs","KTs"
            ],
            "Limp / fold vs Iso AI / call vs 3x Iso": [
                "K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s","J2s",
                "T9s","T8s","T7s","T6s","T5s",
                "98s","97s","96s","95s",
                "87s","86s","85s","84s",
                "76s","75s","74s",
                "65s","64s","63s",
                "54s","53s",
                "43s",
                "A6o","A5o","A4o","A3o","A2o",
                "KJo","KTo","K9o","K8o","K7o","K6o",
                "QJo","QTo","Q9o",
                "JTo","Q8o","Q7o",
                "J9o","J8o",
                "T9o","T8o",
                "98o","97o",
                "87o"
            ],
            "All in": ["88","77","66","55","44","33","22","A9o","A8o","A7o","AKo","AQo","AJo","ATo","A8s","A7s","A6s","A5s","A4s","A3s","A2s"],
            "Fold": ["83o","82o","73o","72o","63o","62o","53o","52o","43o","42o","32o"],
            "Limp / fold vs Iso AI / fold vs NAI Iso": "EVERYTHING_ELSE"
        },
        "buttons": ["2x raise / call AI / jam vs NAI 3b","Limp / fold vs Iso AI / call vs 3x Iso","Limp / fold vs Iso AI / fold vs NAI Iso","All in","Fold"]
    },
    "HU SB 8-10bb": {
        "type": "categorical",
        "data": {
            "2x raise / call AI / jam vs NAI 3b": ["AA","KK","QQ","JJ","TT","99","88","AKs","AQs","AJs","ATs","A9s","A8s","KQs","KJs","KTs","KQo","KJo","AKo","AQo","AJo","ATo"],
            "Limp / fold vs Iso AI / call vs 3x Iso": [
                "J9o","J8o","Q8o","T9o","T8o","98o",
                "Q5s","Q4s","Q3s","Q2s",
                "J6s","J5s","J4s","J3s","J2s",
                "T6s","T5s","95s","84s","74s","64s","63s","54s","53s","43s"
            ],
            "All in": [
                "77","66","55","44","33","22",
                "A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "A7s","A6s","A5s","A4s","A3s","A2s",
                "K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "Q9s","Q8s","Q7s","Q6s",
                "J9s","J8s","J7s",
                "T9s","T8s","T7s",
                "98s","97s","96s",
                "87s","86s","85s","76s","75s","65s",
                "KTo","K9o","K8o","K7o","K6o","K5o",
                "QJo","QTo","Q9o","JTo"
            ],
            "Fold": [
                "93o","92o","83o","82o","73o","72o","63o","62o","53o","52o","43o","42o","32o"
            ],
            "Limp / fold vs Iso AI / fold vs NAI Iso": "EVERYTHING_ELSE"
        },
        "buttons": ["2x raise / call AI / jam vs NAI 3b","Limp / fold vs Iso AI / call vs 3x Iso","Limp / fold vs Iso AI / fold vs NAI Iso","All in","Fold"]
    },
    "HU SB 5-8bb": {
        "type": "categorical",
        "data": {
            "Limp / call vs Iso AI / all-in vs NAI Iso": ["AA","KK","QQ","JJ","TT","99","88"],
            "Limp / fold vs Iso AI / fold vs NAI Iso": [
                "J4s","J3s","J2s",
                "T6s","T5s","T4s","T3s","T2s",
                "96s","95s","94s","93s","92s",
                "85s","84s","83s",
                "74s","73s",
                "64s","63s","62s",
                "54s","53s","52s","43s","42s","32s",
                "Q4o","Q3o","Q2o",
                "J7o","J6o","J5o","J4o","J3o","J2o",
                "T7o","T6o","97o","96o",
                "87o","86o","85o","76o","75o","74o","65o","64o","54o"
            ],
            "Fold": [
                "T5o","T4o","T3o","T2o",
                "95o","94o","93o","92o",
                "84o","83o","82o",
                "73o","72o","62o","52o","42o","32o","63o","53o","43o","82s","72s"
            ],
            "All in": "EVERYTHING_ELSE"
        },
        "buttons": ["Limp / call vs Iso AI / all-in vs NAI Iso","All in","Limp / fold vs Iso AI / fold vs NAI Iso","Fold"]
    },
    "HU SB Push < 10bb": {
        "type": "numerical",
        "data": {
            "AA": 10, "KK": 10, "QQ": 10, "JJ": 10, "TT": 10, "99": 10, "88": 10, "77": 10, "66": 10, "55": 10, "44": 10, "33": 10, "22": 10,

            "AKs": 10, "AQs": 10, "AJs": 10, "ATs": 10, "A9s": 10, "A8s": 10, "A7s": 10, "A6s": 10, "A5s": 10, "A4s": 10, "A3s": 10, "A2s": 10,
            "KQs": 10, "KJs": 10, "KTs": 10, "K9s": 10, "K8s": 10, "K7s": 10, "K6s": 10, "K5s": 10, "K4s": 10,  "K3s": 10,  "K2s": 10,
            "QJs": 10, "QTs": 10, "Q9s": 10, "Q8s": 10, "Q7s": 10, "Q6s": 10, "Q5s": 10, "Q4s": 10,  "Q3s": 10,  "Q2s": 10,
            "JTs": 10, "J9s": 10, "J8s": 10, "J7s": 10, "J6s": 10, "J5s": 10, "J4s": 10, "J3s": 10,  "J2s": 8,
            "T9s": 10, "T8s": 10, "T7s": 10, "T6s": 10, "T5s": 10, "T4s": 9, "T3s": 7,  "T2s": 6,
            "98s": 10, "97s": 10, "96s": 10, "95s": 10, "94s": 6, "93s": 4,  "92s": 3,
            "87s": 10, "86s": 10, "85s": 10, "84s": 10, "83s": 2,  "82s": 2,
            "76s": 10, "75s": 10, "74s": 10, "73s": 2,  "72s": 2,
            "65s": 10, "64s": 10, "63s": 2,  "62s": 2,
            "54s": 10, "53s": 6,  "52s": 2,
            "43s": 5, "42s": 1,
            "32s": 1,

            "AKo": 10, "AQo": 10, "AJo": 10, "ATo": 10, "A9o": 10, "A8o": 10, "A7o": 10, "A6o": 10, "A5o": 10, "A4o": 10, "A3o": 10, "A2o": 10,
            "KQo": 10, "KJo": 10, "KTo": 10, "K9o": 10, "K8o": 10, "K7o": 10, "K6o": 10, "K5o": 10,  "K4o": 10,  "K3o": 10,  "K2o": 10,
            "QJo": 10, "QTo": 10, "Q9o": 10, "Q8o": 10,  "Q7o": 8,  "Q6o": 8,  "Q5o": 7,  "Q4o": 7,  "Q3o": 6,  "Q2o": 6,
            "JTo": 10, "J9o": 10, "J8o": 10,  "J7o": 7,  "J6o": 6,  "J5o": 5,  "J4o": 5,  "J3o": 4,  "J2o": 4,
            "T9o": 10, "T8o": 10,  "T7o": 8,  "T6o": 5,  "T5o": 4,  "T4o": 4,  "T3o": 4,  "T2o": 4,
            "98o": 10,  "97o": 8,  "96o": 5,  "95o": 4,  "94o": 3,  "93o": 3,  "92o": 3,
            "87o": 10, "86o": 5,  "85o": 3,  "84o": 2,  "83o": 1,  "82o": 1,
            "76o": 7, "75o": 2,  "74o": 2,  "73o": 1,  "72o": 1,
            "65o": 2, "64o": 2,  "63o": 1,  "62o": 1,
            "54o": 2,  "53o": 1,  "52o": 1,
            "43o": 1, "42o": 1,
            "32o": 1
        },
        "buttons": ["All in","Fold"]
    },
    "HU BB vs 2x 20bb+": {
        "type": "categorical",
        "data": {
            "Re-Raise 2.5x": ["AA","KK","QQ","JJ"],
            "All in": ["AKo","AQo","AJo","ATo","AKs","AQs","AJs","ATs","TT","99","88","77","66","55","44"],
            "Fold": [
                "Q3o","Q2o",
                "J5o","J4o","J3o","J2o",
                "T5o","T4o","T3o","T2o",
                "95o","94o","93o","92o",
                "85o","84o","83o","82o",
                "74o","73o","72o",
                "63o","62o",
                "53o","52o",
                "43o","42o","32o"
            ],
            "Call": "EVERYTHING_ELSE"
        },
        "buttons": ["Re-Raise 2.5x","All in","Call","Fold"]
    },
    "HU BB vs 2x 16-20bb": {
        "type": "categorical",
        "data": {
            "Re-Raise 2.5x": ["AA","KK","QQ"],
            "All in": ["JJ","A9s","AKo","AQo","AJo","ATo","AKs","AQs","AJs","ATs","TT","99","88","77","66","55","44"],
            "Fold": [
                "Q3o","Q2o",
                "J5o","J4o","J3o","J2o",
                "T5o","T4o","T3o","T2o",
                "95o","94o","93o","92o",
                "85o","84o","83o","82o",
                "74o","73o","72o",
                "63o","62o",
                "53o","52o",
                "43o","42o","32o","64o","T6o"
            ],
            "Call": "EVERYTHING_ELSE"
        },
        "buttons": ["Re-Raise 2.5x","All in","Call","Fold"]
    },
    "HU BB vs 2x 13-16bb": {
        "type": "categorical",
        "data": {
            "Re-Raise 2.5x": ["AA","KK","QQ","JJ"],
            "All in": ["33","22","A9s","A9o","A8o","A8s","A7s","AKo","AQo","AJo","ATo","AKs","AQs","AJs","ATs","TT","99","88","77","66","55","44"],
            "Fold": [
                "Q3o","Q2o",
                "J5o","J4o","J3o","J2o",
                "T5o","T4o","T3o","T2o",
                "95o","94o","93o","92o",
                "85o","84o","83o","82o",
                "74o","73o","72o",
                "63o","62o",
                "53o","52o",
                "43o","42o","32o","64o","T6o","J6o","Q4o"
            ],
            "Call": "EVERYTHING_ELSE"
        },
        "buttons": ["Re-Raise 2.5x","All in","Call","Fold"]
    },
    "HU BB vs 2x 10-13bb": {
        "type": "categorical",
        "data": {
            "Re-Raise 2.5x": ["AA","KK"],
            "All in": ["33","22","A9s","A9o","A8o","A8s","A7s","AKo","AQo","AJo","ATo","AKs","AQs","AJs","ATs","TT","99","88","77","66","55","44","A6s","A5s","A4s","A3s","A2s","KQs","KJs","KQo","A7o","A6o","A5o","A4o","QQ","JJ"],
            "Fold": [
                "Q3o","Q2o",
                "J5o","J4o","J3o","J2o",
                "T5o","T4o","T3o","T2o",
                "95o","94o","93o","92o",
                "85o","84o","83o","82o",
                "74o","73o","72o",
                "63o","62o",
                "53o","52o",
                "43o","42o","32o","64o","T6o","J6o","Q4o",
                "96o","Q5o"
            ],
            "Call": "EVERYTHING_ELSE"
        },
        "buttons": ["Re-Raise 2.5x","All in","Call","Fold"]
    },
    "HU BB vs 2x < 10bb": {
        "type": "categorical",
        "data": {
            "All in": ["33","22","A9s","A9o","A8o","A8s","A7s","AKo","AQo","AJo","ATo","AKs","AQs","AJs","ATs","TT","99","88","77","66","55","44","A6s","A5s","A4s","A3s","A2s","KQs","KJs","KQo","A7o","A6o","A5o","A4o","QQ","JJ","AA","KK","KTs","K9s","K8s","K7s","QJs","QTs","Q9s","JTs","J9s","T9s","KJo","KTo","K9o","QJo","A3o","A2o"],
            "Fold": [
                "Q3o","Q2o",
                "J5o","J4o","J3o","J2o",
                "T5o","T4o","T3o","T2o",
                "95o","94o","93o","92o",
                "85o","84o","83o","82o",
                "74o","73o","72o",
                "63o","62o",
                "53o","52o",
                "43o","42o","32o","64o","T6o","J6o","Q4o",
                "96o","Q5o","54o","75o","65o","86o","97o",
                "T7o","J7o","Q7o","Q6o","K3o","K2o"
            ],
            "Call": "EVERYTHING_ELSE"
        },
        "buttons": ["All in","Call","Fold"]
    },
    "HU BB vs All In": {
        "type": "numerical",
        "data": {
            "AA": 20, "KK": 20, "QQ": 20, "JJ": 20, "TT": 20, "99": 20, "88": 20, "77": 20, "66": 20, "55": 20, "44": 14, "33": 10, "22": 8,
            
            "AKs": 20, "AQs": 20, "AJs": 20, "ATs": 20, "A9s": 20, "A8s": 20, "A7s": 18, "A6s": 15, "A5s": 15, "A4s": 14, "A3s": 12, "A2s": 12,
            "KQs": 16, "KJs": 15, "KTs": 12, "K9s": 10, "K8s": 9, "K7s": 9, "K6s": 8, "K5s": 7, "K4s": 7, "K3s": 7, "K2s": 7,
            "QJs": 13, "QTs": 12, "Q9s": 9, "Q8s": 8, "Q7s": 7, "Q6s": 7, "Q5s": 6, "Q4s": 6, "Q3s": 6, "Q2s": 5,
            "JTs": 10, "J9s": 9, "J8s": 7, "J7s": 7, "J6s": 6, "J5s": 5, "J4s": 5, "J3s": 4, "J2s": 4,
            "T9s": 9, "T8s": 7, "T7s": 6, "T6s": 4, "T5s": 4, "T4s": 4, "T3s": 4, "T2s": 3,
            "98s": 7, "97s": 6, "96s": 4, "95s": 4, "94s": 3, "93s": 3, "92s": 3,
            "87s": 6, "86s": 4, "85s": 4, "84s": 3, "83s": 3, "82s": 3,
            "76s": 4, "75s": 4, "74s": 3, "73s": 3, "72s": 3, 
            "65s": 4, "64s": 3, "63s": 3, "62s": 3, 
            "54s": 4, "53s": 3, "52s": 3,
            "43s": 3, "42s": 3, 
            "32s": 3, 

            "AKo": 20, "AQo": 20, "AJo": 20, "ATo": 20, "A9o": 20, "A8o": 15, "A7o": 14, "A6o": 11, "A5o": 11, "A4o": 11, "A3o": 10, "A2o": 10,
            "KQo": 12, "KJo": 11, "KTo": 10, "K9o": 9, "K8o": 9, "K7o": 8, "K6o": 7, "K5o": 7, "K4o": 6, "K3o": 6, "K2o": 6,
            "QJo": 10, "QTo": 9, "Q9o": 8, "Q8o": 7, "Q7o": 6, "Q6o": 5, "Q5o": 5, "Q4o": 4, "Q3o": 4, "Q2o": 4,
            "JTo": 8, "J9o": 7, "J8o": 6, "J7o": 4, "J6o": 4, "J5o": 4, "J4o": 4, "J3o": 3, "J2o": 3,
            "T9o": 6, "T8o": 4, "T7o": 4, "T6o": 4, "T5o": 4, "T4o": 3, "T3o": 3, "T2o": 3,
            "98o": 4, "97o": 4, "96o": 4, "95o": 3, "94o": 3, "93o": 2, "92o": 2,
            "87o": 4, "86o": 4, "85o": 3, "84o": 3, "83o": 2, "82o": 2,
            "76o": 3, "75o": 3, "74o": 3, "73o": 2, "72o": 2,
            "65o": 3, "64o": 3, "63o": 2, "62o": 2,
            "54o": 3, "53o": 2, "52o": 2,
            "43o": 2, "42o": 2,
            "32o": 2
        },
        "buttons": ["Call","Fold"]
    },
    "HU BB vs Limp 20bb+": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA","KK","QQ","JJ","TT","99","88",
                "AKs","AQs","AJs","ATs","A9s","A8s",
                "KQs","KJs","KTs","QJs","QTs","JTs",
                "AKo","AQo","AJo"
            ],
            "All in": ["77","66","55","44","ATo","A9o","A8o","A7o"],
            "3x raise / fold vs all in": [
                "A7s","A6s","A5s",
                "K9s","K8s","K7s","Q9s","Q8s","J9s","J8s","T9s","T8s","98s",
                "KQo","KJo","KTo","K9o","K8o","QJo","QTo","Q9o","JTo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","3x raise / fold vs all in","Check"]
    },
    "HU BB vs Limp 16-20bb": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA","KK","QQ","JJ","TT","99",
                "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s",
                "KQs","KJs","KTs","QJs","QTs","JTs"
            ],
            "All in": [
                "77","66","55","44","88","33","22",
                "ATo","A9o","A8o","A7o",
                "A5s","A4s","A3s","A2s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o"
                ],
            "3x raise / fold vs all in": [
                "K9s","K8s","K7s","Q9s","Q8s","J9s","J8s","T9s","T8s","98s",
                "KQo","KJo","KTo","K9o","K8o","QJo","QTo","Q9o","JTo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","3x raise / fold vs all in","Check"]
    },
    "HU BB vs Limp 13-16bb": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA","KK","QQ","JJ","TT","99",
                "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s",
                "KQs","KJs","KTs","QJs","QTs","JTs"
            ],
            "All in": [
                "77","66","55","44","88","33","22",
                "ATo","A9o","A8o","A7o",
                "A5s","A4s","A3s","A2s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o"
                ],
            "3x raise / fold vs all in": [
                "K9s","K8s","K7s","Q9s","Q8s","J9s","J8s","T9s","T8s","98s",
                "KQo","KJo","KTo","K9o","K8o","QJo","QTo","Q9o","JTo"
            ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","3x raise / fold vs all in","Check"]
    },
    "HU BB vs Limp 10-13bb": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA","KK","QQ","JJ","TT","99",
                "AKs","AQs","AJs","ATs",
                "KQs","KJs","KTs","QJs","QTs","JTs"
            ],
            "All in": [
                "77","66","55","44","88","33","22",
                "ATo","A9o","A8o","A7o",
                "A5s","A4s","A3s","A2s","A9s","A8s","A7s","A6s",
                "K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "Q9s","Q8s","Q7s","J9s","J8s","T9s","T8s","98s","97s","87s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o","K8o","K7o","QJo","QTo","JTo"
                ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","Check"]
    },
    "HU BB vs Limp < 10bb": {
        "type": "categorical",
        "data": {
            "3x raise / call vs all in": [
                "AA","KK","QQ","JJ","TT"
            ],
            "All in": [
                "AKs","AQs","AJs","ATs",
                "KQs","KJs","KTs","QJs","QTs","JTs",
                "99","77","66","55","44","88","33","22",
                "ATo","A9o","A8o","A7o",
                "A5s","A4s","A3s","A2s","A9s","A8s","A7s","A6s",
                "K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
                "Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
                "J9s","J8s","T9s","T8s","98s",
                "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
                "KQo","KJo","KTo","K9o","K8o","K7o","K6o","K5o","K4o","K3o","K2o",
                "QJo","QTo","JTo","Q9o","Q8o"
                ],
            "Check": "EVERYTHING_ELSE"
        },
        "buttons": ["3x raise / call vs all in","All in","Check"]
    },
}

# Организация категорий для UI
SPIN_CATEGORIES = {
    "BU (Button)": ["BU 13-16 BB","BU 10-13 BB","BU < 10 BB"],
    "SB vs BU": ["SB vs BU MR 13-16 BB","SB vs BU MR 10-13 BB","SB vs BU MR < 10 BB","SB vs BU AI < 25 BB","SB vs BU Limp 13-16 BB","SB vs BU Limp 10-13 BB","SB vs BU Limp < 10 BB"],
    "SB vs BB": ["SB vs BB 13-16 BB","SB vs BB 10-13 BB","SB vs BB 8-10 BB","SB vs BB < 10 BB"],
    "BB vs BU": ["BB vs BU MR 13-16 BB","BB vs BU MR 10-13 BB","BB vs BU MR < 10 BB","BB vs BU AI","BB vs BU Limp 13-16 BB","BB vs BU Limp 10-13 BB","BB vs BU Limp < 10 BB"],
    "BB vs SB": ["BB vs SB MR 13-16 BB","BB vs SB MR 10-13 BB","BB vs SB AI","BB vs SB Limp 13-16 BB","BB vs SB Limp 10-13 BB","BB vs SB Limp < 10 BB"],
    "BB vs 2pp": ["BB vs 2pp MR 13-16 BB","BB vs 2pp MR 10-13 BB","BB vs 2pp MR < 10 BB","BB vs 2pp AI","BB vs 2pp Limp 13-16 BB","BB vs 2pp Limp 10-13 BB","BB vs 2pp Limp < 10 BB"],
}

HU_CATEGORIES = {
    "HU SB": ["HU SB 20bb+","HU SB 16-20bb","HU SB 13-16bb","HU SB 10-13bb","HU SB 8-10bb","HU SB 5-8bb","HU SB Push < 10bb"],
    "HU BB vs Raise": ["HU BB vs 2x 20bb+","HU BB vs 2x 16-20bb","HU BB vs 2x 13-16bb","HU BB vs 2x 10-13bb","HU BB vs 2x < 10bb","HU BB vs All In"],
    "HU BB vs Limp": ["HU BB vs Limp 20bb+","HU BB vs Limp 16-20bb","HU BB vs Limp 13-16bb","HU BB vs Limp 10-13bb","HU BB vs Limp < 10bb"],
}

# ============================================================
# LOGIC
# ============================================================
def get_hand_notation(c1, c2):
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]
    if RANK_ORDER[r1] < RANK_ORDER[r2]:
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    if r1 == r2:
        return r1 + r2
    elif s1 == s2:
        return r1 + r2 + "s"
    else:
        return r1 + r2 + "o"

def calculate_chip_ev(
    hero_stack: int,
    villain_stack: int,
    hero_invested: int,
    villain_invested: int,
    hero_equity: float,
    pot: int,
    fold_equity: float = 0.0
) -> float:
    """Больше не используется для основного расчёта, оставлено для совместимости."""
    risk = hero_invested
    showdown_ev = (hero_equity * pot) - ((1 - hero_equity) * risk)
    return round(showdown_ev, 2)

def get_correct_action(notation: str, stack: float, spot_name: str, is_hu: bool = False) -> str:
    charts = HU_CHARTS if is_hu else CHARTS
    chart = charts.get(spot_name)
    if not chart:
        return "Fold"

    if chart["type"] == "categorical":
        for action, hands in chart["data"].items():
            if hands == "EVERYTHING_ELSE":
                continue
            if notation in hands:
                return action
        for action, hands in chart["data"].items():
            if hands == "EVERYTHING_ELSE":
                return action
        return "Check" if "Check" in chart["buttons"] else "Fold"
    elif chart["type"] == "numerical":
        threshold = chart["data"].get(notation, 0)
        main_action = "All in" if "All in" in chart["buttons"] else "Call"
        return main_action if stack <= threshold else "Fold"
    return "Fold"

def get_stack_for_spot(spot_name):
    s = spot_name.lower()
    if "20bb+" in s or "20bb +" in s:
        return random.randint(20, 30)
    elif "16-20" in s:
        return random.randint(16, 20)
    elif "13-16" in s:
        return random.randint(13, 16)
    elif "10-13" in s:
        return random.randint(10, 13)
    elif "8-10" in s:
        return random.randint(8, 10)
    elif "5-8" in s:
        return random.randint(5, 8)
    elif "< 8" in s or "<8" in s:
        return random.randint(2, 7)
    elif "< 10" in s or "<10" in s or "push" in s:
        return random.randint(2, 9)
    elif "< 25" in s or "< 16" in s or "vs ai" in s or "all in" in s:
        return random.randint(2, 24)
    elif "16+" in s:
        return random.randint(16, 25)
    else:
        return random.randint(5, 25)

def pick_relevant_hand(spot_name: str, is_hu: bool) -> tuple[Optional[str], Optional[str], Optional[list]]:
    charts = HU_CHARTS if is_hu else CHARTS
    chart = charts.get(spot_name)
    if not chart:
        return None, None, None

    chart_hands = set()
    for action, hands in chart["data"].items():
        if isinstance(hands, list):
            for h in hands:
                chart_hands.add(h)
        elif isinstance(hands, dict):
            for h in hands.keys():
                chart_hands.add(h)

    pool = chart_hands & RELEVANT_HANDS
    border_hands = RELEVANT_HANDS - chart_hands
    pool = pool | (border_hands & {
        "K6s","K5s","Q6s","Q7s","Q8s","J7s","J8s","T7s","T8s","98s","97s","96s","87s","86s","76s","75s","65s","64s","54s",
        "K6o","K7o","K8o","Q8o","Q9o","J8o","J9o","T8o","T9o","98o"
    })
    if not pool:
        pool = RELEVANT_HANDS

    notation = random.choice(list(pool))
    deck = list(itertools.product(RANKS, SUITS))
    for _ in range(1000):
        card1_rank, card1_suit = random.choice(RANKS), random.choice(SUITS)
        card2_rank, card2_suit = random.choice(RANKS), random.choice(SUITS)
        while (card1_rank, card1_suit) == (card2_rank, card2_suit):
            card2_rank, card2_suit = random.choice(RANKS), random.choice(SUITS)
        n = get_hand_notation((card1_rank, card1_suit), (card2_rank, card2_suit))
        if n == notation:
            full_cards_str = f"{card1_rank}{card1_suit}{card2_rank}{card2_suit}"
            return full_cards_str, notation, [(card1_rank, card1_suit), (card2_rank, card2_suit)]
    return None, None, None

def get_action_color(action):
    a = action.lower()
    if "all in" in a or "jam" in a or "rejam" in a:
        return "#e74c3c"
    if "raise" in a:
        return "#e67e22"
    if "call" in a:
        return "#27ae60"
    if "check" in a:
        return "#16a085"
    if "limp" in a:
        return "#2980b9"
    return "#2c3e50"

# ============================================================
# DATA CLASSES & PARSER (полностью переписана логика cEV)
# ============================================================
@dataclass
class PlayerAction:
    street: str
    player: str
    action: str
    amount: int = 0
    to_amount: int = 0
    is_allin: bool = False

@dataclass
class HandState:
    hand_id: str
    hero_cards: str = ""
    hero_notation: str = ""
    hero_stack_start: int = 0
    bb: int = 20
    hero_pos: str = ""
    is_hu: bool = False
    actions: List['PlayerAction'] = field(default_factory=list)
    hero_invested: int = 0          # сколько Hero реально вложил в банк (с учётом возврата)
    hero_won: int = 0
    is_preflop_allin: bool = False
    final_pot: int = 0
    opp_cards: dict = field(default_factory=dict)   # PlayerName -> "AcKc"
    player_positions: dict = field(default_factory=dict)
    net_chips: int = 0              # hero_won - hero_invested
    # Дополнительные поля для All-in Adjusted cEV
    equity_vs_range: float = 0.0
    preflop_showdown: bool = False
    # Pure EV fields
    pure_ev: float = 0.0            # математический EV, не зависит от runout
    dead_money: int = 0             # сколько оппонента в банке до решения Hero
    risk_amount: int = 0            # сколько Hero рисует в all-in

class GGPokerParser:
    ACTION_RE = re.compile(
        r'^(\S+): (folds|checks|calls|bets|raises|posts small blind|posts big blind)(?: (\d+))?(?: to (\d+))?( and is all-in)?',
        re.MULTILINE
    )

    @staticmethod
    def parse_hand(hand_text: str) -> Optional[HandState]:
        hand_id_m = re.search(r'Poker Hand #(\S+):', hand_text)
        if not hand_id_m: return None

        m_blinds = re.search(r'Level\d+\((\d+)/(\d+)\)', hand_text)
        bb = int(m_blinds.group(2)) if m_blinds else 20

        m_hero_stack = re.search(r'Seat \d+: Hero \((\d+) in chips\)', hand_text)
        if not m_hero_stack: return None

        hero_cards_m = re.search(r'Dealt to Hero \[(..) (..)\]', hand_text)
        if not hero_cards_m: return None

        hero_notation = get_hand_notation(hero_cards_m.group(1), hero_cards_m.group(2))
        hero_full_cards_str = f"{hero_cards_m.group(1)}{hero_cards_m.group(2)}"
        state = HandState(
            hand_id=hand_id_m.group(1),
            hero_cards=hero_full_cards_str,
            hero_notation=hero_notation,
            hero_stack_start=int(m_hero_stack.group(1)),
            bb=bb
        )

        # Позиции
        m_btn = re.search(r'Seat #(\d+) is the button', hand_text)
        m_seats = re.findall(r'Seat (\d+): (.*?) \(', hand_text)
        if m_btn and m_seats:
            btn_seat = int(m_btn.group(1))
            seats_dict = {int(s[0]): s[1] for s in m_seats}
            sorted_s = sorted(seats_dict.keys())
            state.is_hu = len(sorted_s) == 2
            btn_idx = sorted_s.index(btn_seat)
            for s_num in sorted_s:
                p_name = seats_dict[s_num]
                if state.is_hu:
                    pos = "SB" if s_num == btn_seat else "BB"
                else:
                    if s_num == btn_seat: pos = "BU"
                    elif s_num == sorted_s[(btn_idx+1)%len(sorted_s)]: pos = "SB"
                    else: pos = "BB"
                state.player_positions[p_name] = pos
                if p_name == "Hero": state.hero_pos = pos

        # Парсинг действий
        current_street = "PREFLOP"
        hero_contrib_raw = 0
        uncalled_returned = 0
        for line in hand_text.splitlines():
            if "*** FLOP ***" in line: current_street = "FLOP"
            elif "*** SHOWDOWN ***" in line: current_street = "SHOWDOWN"

            m = GGPokerParser.ACTION_RE.search(line)
            if m:
                act = PlayerAction(
                    street=current_street,
                    player=m.group(1),
                    action=m.group(2),
                    amount=int(m.group(3)) if m.group(3) else 0,
                    to_amount=int(m.group(4)) if m.group(4) else 0,
                    is_allin=bool(m.group(5))
                )
                state.actions.append(act)

                if act.player == "Hero":
                    if act.action in ["posts small blind", "posts big blind", "calls", "bets"]:
                        hero_contrib_raw += act.amount
                    elif act.action == "raises":
                        hero_contrib_raw = act.to_amount

            # Карты оппонента на вскрытии
            opp_show = re.search(r'^(\S+): shows \[(..) (..)\]', line)
            if opp_show and opp_show.group(1) != 'Hero':
                state.opp_cards[opp_show.group(1)] = f"{opp_show.group(2)}{opp_show.group(3)}"

        # Возвращённая часть ставки
        uncalled = re.search(r'Uncalled bet \((\d+)\) returned to Hero', hand_text)
        if uncalled:
            uncalled_returned = int(uncalled.group(1))

        state.hero_invested = hero_contrib_raw - uncalled_returned

        # Итоговый банк и выигрыш Hero
        pot_match = re.search(r'Total pot (\d+)', hand_text)
        state.final_pot = int(pot_match.group(1)) if pot_match else 0
        won_matches = re.findall(r'Hero (?:collected|won).*?\(?(\d+)\)?', hand_text)
        state.hero_won = sum(int(x) for x in won_matches)

        state.net_chips = state.hero_won - state.hero_invested

        # Префлоп олл-ин и вскрытие
        pf_actions = [a for a in state.actions if a.street == "PREFLOP"]
        hero_ai = any(a.player == "Hero" and a.is_allin for a in pf_actions)
        state.is_preflop_allin = hero_ai
        state.preflop_showdown = hero_ai and len(state.opp_cards) > 0

        # =============================================
        # PURE EV CALCULATION
        # =============================================

        try:
            # Вычисление dead_money (вложено оппонентом до решения Hero)
            dead_money = 0
            hero_already_invested = 0  # сколько вложил Hero до своего решения

            for action in pf_actions:
                if action.action in ["posts small blind", "posts big blind", "calls", "bets"]:
                    amount = action.amount
                elif action.action == "raises":
                    amount = action.to_amount
                else:
                    continue

                if action.player == "Hero":
                    hero_already_invested += amount
                else:
                    dead_money += amount

            state.dead_money = dead_money
            state.risk_amount = state.hero_invested - hero_already_invested  # сколько Hero рискует в последнем решении

            # Equity для all-in cases
            if state.preflop_showdown:
                villain_cards = list(state.opp_cards.values())
                # Для простоты берём первого оппонента (в рамках Spin&Go обычно один)
                state.equity_vs_range = calculate_equity(state.hero_cards, villain_cards[:1], iterations=5000)

                # Правильная формула all-in EV:
                # pure_ev = equity * final_pot - (1 - equity) * hero_invested
                equity = state.equity_vs_range
                state.pure_ev = equity * state.final_pot - (1 - equity) * state.hero_invested

            else:
                # Для фолдов и выигрышей без вскрытия pure_ev = фактический результат
                state.pure_ev = state.net_chips

        except Exception as e:
            print(f"PURE EV CALC ERROR: {e}")
            state.pure_ev = state.net_chips

        return state

class PreflopSpotMapper:
    @staticmethod
    def resolve_spot(state: HandState) -> Optional[str]:
        stk = state.hero_stack_start / state.bb if state.bb > 0 else 100
        pre_actions = [a for a in state.actions if a.street == "PREFLOP"]
        hero_idx = -1
        for i, a in enumerate(pre_actions):
            if a.player == "Hero" and a.action not in ["posts small blind", "posts big blind"]:
                hero_idx = i
                break
        if hero_idx == -1: return None
        actions_before = pre_actions[:hero_idx]

        if state.is_hu:
            if state.hero_pos == "SB":
                if stk <= 10: return "HU SB Push < 10bb"
                if stk <= 13: return "HU SB 10-13bb"
                if stk <= 16: return "HU SB 13-16bb"
                return "HU SB 20bb+"
            else:  # Hero BB
                opp_last = next((a for a in reversed(actions_before) if state.player_positions.get(a.player) == "SB" and a.player != "Hero"), None)
                if not opp_last: return "HU BB vs SB Fold"
                if opp_last.is_allin: return "HU BB vs All In"
                elif opp_last.action == "raises":
                    if stk <= 10: return "HU BB vs 2x < 10bb"
                    if stk <= 13: return "HU BB vs 2x 10-13bb"
                    if stk <= 16: return "HU BB vs 2x 13-16bb"
                    if stk <= 20: return "HU BB vs 2x 16-20bb"
                    return "HU BB vs 2x 20bb+"
                elif opp_last.action == "calls":
                    if stk <= 10: return "HU BB vs Limp < 10bb"
                    if stk <= 13: return "HU BB vs Limp 10-13bb"
                    if stk <= 16: return "HU BB vs Limp 13-16bb"
                    if stk <= 20: return "HU BB vs Limp 16-20bb"
                    return "HU BB vs Limp 20bb+"
        else:
            if state.hero_pos == "BU":
                if stk < 10: return "BU < 10 BB"
                if stk <= 13: return "BU 10-13 BB"
                return "BU 13-16 BB"
            elif state.hero_pos == "SB":
                bu_last = next((a for a in reversed(actions_before) if state.player_positions.get(a.player) == "BU" and a.player != "Hero"), None)
                if bu_last and bu_last.action != "folds":
                    if bu_last.is_allin: return "SB vs BU AI < 25 BB"
                    if bu_last.action == "raises":
                        if stk <= 10: return "SB vs BU MR < 10 BB"
                        if stk <= 13: return "SB vs BU MR 10-13 BB"
                        return "SB vs BU MR 13-16 BB"
                    if bu_last.action == "calls":
                        if stk <= 10: return "SB vs BU Limp < 10 BB"
                        if stk <= 13: return "SB vs BU Limp 10-13 BB"
                        return "SB vs BU Limp 13-16 BB"
                else:
                    if stk <= 10: return "SB vs BB < 10 BB"
                    if stk <= 13: return "SB vs BB 10-13 BB"
                    return "SB vs BB 13-16 BB"
            elif state.hero_pos == "BB":
                bu_last = next((a for a in reversed(actions_before) if state.player_positions.get(a.player) == "BU" and a.player != "Hero"), None)
                sb_last = next((a for a in reversed(actions_before) if state.player_positions.get(a.player) == "SB" and a.player != "Hero"), None)
                if bu_last and bu_last.action != "folds":
                    if bu_last.is_allin: return "BB vs BU AI"
                    if bu_last.action == "raises":
                        if stk <= 10: return "BB vs BU MR < 10 BB"
                        if stk <= 13: return "BB vs BU MR 10-13 BB"
                        return "BB vs BU MR 13-16 BB"
                    if bu_last.action == "calls":
                        if stk <= 13: return "BB vs BU Limp 10-13 BB"
                        return "BB vs BU Limp 13-16 BB"
                elif (not bu_last or bu_last.action == "folds") and sb_last and sb_last.action != "folds":
                    if sb_last.is_allin: return "HU BB vs All In"
                    if sb_last.action == "raises":
                        if stk <= 10: return "HU BB vs 2x < 10bb"
                        if stk <= 13: return "HU BB vs 2x 10-13bb"
                        if stk <= 16: return "HU BB vs 2x 13-16bb"
                        if stk <= 20: return "HU BB vs 2x 16-20bb"
                        return "HU BB vs 2x 20bb+"
                    if sb_last.action == "calls":
                        if stk <= 10: return "HU BB vs Limp < 10bb"
                        if stk <= 13: return "HU BB vs Limp 10-13bb"
                        if stk <= 16: return "HU BB vs Limp 13-16bb"
                        if stk <= 20: return "HU BB vs Limp 16-20bb"
                        return "HU BB vs Limp 20bb+"
        return None

def analyze_gg_histories(uploaded_files):
    overall = {
        'total_real_chip_result': 0,
        'total_tournament_cev': 0,          # сумма net_chips по всем раздачам (= Pure Preflop cEV)
        'total_allin_adj_cev': 0,
        'total_hands_processed': 0,
        'total_decisions_verified': 0,
        'total_correct_decisions': 0,
        'tournaments_finished_count': 0,
        'total_finished_cev': 0,            # сумма tournament_cev завершённых турниров
        'tournaments_processed_count': len(uploaded_files),
        'tournament_reports': [],
        'all_errors': []  # Ошибочные решения для интерактивного просмотра
    }

    for f in uploaded_files:
        content = f.getvalue().decode('utf-8', errors='ignore')
        hands_raw = re.split(r'Poker Hand #', content)
        hands_texts = ["Poker Hand #" + h for h in hands_raw if h.strip()]

        report = {
            'file_name': f.name,
            'starting_stack': None,
            'final_stack': None,
            'tournament_finished': False,
            'real_chip_result': 0,
            'tournament_cev': 0,             # сумма net_chips
            'allin_adj_cev': 0,
            'hands_processed': 0,
            'decisions_verified': 0,
            'correct_decisions': 0,
            'all_in_details': [],
            'errors': []  # Ошибки в этом турнире
        }

        current_stack = None  # будет обновляться после каждой раздачи

        for h_text in hands_texts:
            state = GGPokerParser.parse_hand(h_text)
            if not state: continue

            report['hands_processed'] += 1
            if report['starting_stack'] is None:
                report['starting_stack'] = state.hero_stack_start
                current_stack = state.hero_stack_start

            # Чистый результат раздачи (Pure Preflop cEV)
            hand_cev = state.hero_won - state.hero_invested
            report['tournament_cev'] += hand_cev

            # All-in Adjusted cEV (только если было вскрытие)
            adj_cev = 0.0
            if state.preflop_showdown:
                adj_cev = state.equity_vs_range * state.final_pot - state.hero_invested
                report['allin_adj_cev'] += adj_cev
                report['all_in_details'].append({
                    'hand': state.hero_notation,
                    'villain': ", ".join(state.opp_cards.keys()),
                    'equity': f"{state.equity_vs_range*100:.1f}%",
                    'pot': state.final_pot,
                    'invested': state.hero_invested,
                    'pure_ev': f"{hand_cev:+.1f}",
                    'adj_ev': f"{adj_cev:+.1f}"
                })

            # Обновление стека (фактический)
            current_stack = state.hero_stack_start + hand_cev

            # Проверка префлоп решения
            spot = PreflopSpotMapper.resolve_spot(state)
            if spot:
                correct_act = get_correct_action(state.hero_notation, state.hero_stack_start / state.bb, spot, state.is_hu)
                
                # Получаем ВСЕ действия Hero на PREFLOP (кроме постинга блайндов)
                hero_pf_actions = [a for a in state.actions 
                    if a.player == "Hero" 
                    and a.street == "PREFLOP" 
                    and a.action not in ["posts small blind", "posts big blind"]]
                
                if hero_pf_actions:
                    report['decisions_verified'] += 1
                    
                    # Проверяем ПОСЛЕДНЕЕ действие (которое определяет финальный выбор)
                    hero_last_action = hero_pf_actions[-1]
                    
                    c_low = correct_act.lower()
                    h_act = hero_last_action.action.lower()
                    is_correct = False
                    
                    if hero_last_action.is_allin and ("all in" in c_low or "jam" in c_low): 
                        is_correct = True
                    elif h_act == "raises" and ("raise" in c_low or "re-raise" in c_low): 
                        is_correct = True
                    elif h_act == "calls" and "call" in c_low: 
                        is_correct = True
                    elif h_act == "folds" and "fold" in c_low: 
                        is_correct = True
                    elif h_act == "checks" and "check" in c_low: 
                        is_correct = True
                    
                    if is_correct:
                        report['correct_decisions'] += 1
                    else:
                        # Получаем действие оппонента перед последним действием Hero
                        opp_last_action = 'N/A'
                        non_hero_actions = [a for a in state.actions if a.street == "PREFLOP" and a.player != "Hero"]
                        if non_hero_actions:
                            opp_last_action = non_hero_actions[-1].action
                        
                        # Сохраняем информацию об ошибке
                        error_info = {
                            'tournament': f.name,
                            'hand_id': state.hand_id,
                            'hero_cards': state.hero_notation,
                            'position': state.hero_pos,
                            'stack_bb': round(state.hero_stack_start / state.bb, 2),
                            'spot': spot,
                            'correct_action': correct_act,
                            'hero_action': hero_last_action.action,
                            'is_allin': hero_last_action.is_allin,
                            'opponent_last_action': opp_last_action,
                            'hand_net_result': state.net_chips,
                            'hand_pure_ev': round(state.pure_ev, 1)
                        }
                        report['errors'].append(error_info)
                        overall['all_errors'].append(error_info)

        report['final_stack'] = current_stack if current_stack is not None else 300
        report['real_chip_result'] = report['final_stack'] - report['starting_stack']
        report['tournament_finished'] = report['final_stack'] <= 0 or report['final_stack'] >= 900

        overall['tournament_reports'].append(report)

        overall['total_real_chip_result'] += report['real_chip_result']
        overall['total_tournament_cev'] += report['tournament_cev']
        overall['total_allin_adj_cev'] += report['allin_adj_cev']
        overall['total_hands_processed'] += report['hands_processed']
        overall['total_decisions_verified'] += report['decisions_verified']
        overall['total_correct_decisions'] += report['correct_decisions']
        if report['tournament_finished']:
            overall['tournaments_finished_count'] += 1
            overall['total_finished_cev'] += report['tournament_cev']

    return overall

# ============================================================
# STREAMLIT CONFIG
# ============================================================
st.set_page_config(
    page_title="Preflop Trainer Pro", 
    layout="wide", 
    initial_sidebar_state="auto"
)

# CSS стили (такие же как в оригинале, оставляем без изменений)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}
.stApp {
    background: linear-gradient(135deg, #0a0f0d 0%, #0d1a14 50%, #0a120e 100%);
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent !important;}
.metric-card {
    background: linear-gradient(135deg, #1a2e22 0%, #0f1f17 100%);
    border: 1px solid #2a4a32;
    border-radius: 16px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
}
.metric-label {
    color: #6b9e7a;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.metric-value {
    color: #e8f5e9;
    font-size: 32px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1;
}
.spot-pill {
    background: linear-gradient(135deg, #1e3a28 0%, #152a1e 100%);
    border: 1px solid #2e5a3e;
    border-radius: 24px;
    padding: 10px 20px;
    color: #7dc98e;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
    display: inline-block;
    margin-bottom: 4px;
}
.card-container {
    display: flex;
    gap: 12px;
    justify-content: center;
    margin: 8px 0;
}
.playing-card {
    width: 72px;
    height: 96px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.15);
    border: 2px solid rgba(255,255,255,0.1);
    background: #f8f4f0;
    user-select: none;
    transition: transform 0.2s;
    animation: card-flip 0.3s ease-out;
}
@keyframes card-flip {
    from { transform: rotateY(90deg) scale(0.8); opacity: 0; }
    to { transform: rotateY(0deg) scale(1); opacity: 1; }
}
.card-red { color: #c0392b; }
.card-black { color: #1a1a1a; }
.hand-badge {
    background: linear-gradient(135deg, #2d5a3d, #1e3f2a);
    border: 2px solid #4a8a5e;
    border-radius: 12px;
    padding: 8px 20px;
    color: #a8d5b5;
    font-size: 22px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 2px;
    display: inline-block;
}
.progress-outer {
    background: #1a2e22;
    border-radius: 8px;
    height: 8px;
    margin: 6px 0;
    overflow: hidden;
    border: 1px solid #2a4a32;
}
.progress-inner {
    height: 100%;
    border-radius: 8px;
    transition: width 0.5s ease;
    background: linear-gradient(90deg, #2ecc71, #27ae60);
}
.banner-correct {
    background: linear-gradient(135deg, #1a3a24, #0d2a17);
    border: 2px solid #27ae60;
    border-radius: 14px;
    padding: 16px 20px;
    color: #2ecc71;
    font-weight: 700;
    font-size: 18px;
    text-align: center;
    animation: pop-in 0.2s ease-out;
    margin: 8px 0;
}
.banner-wrong {
    background: linear-gradient(135deg, #3a1a1a, #2a0d0d);
    border: 2px solid #e74c3c;
    border-radius: 14px;
    padding: 16px 20px;
    color: #e74c3c;
    font-weight: 700;
    font-size: 15px;
    text-align: center;
    animation: shake 0.3s ease-out;
    margin: 8px 0;
}
@keyframes pop-in {
    0% { transform: scale(0.95); opacity: 0; }
    60% { transform: scale(1.02); }
    100% { transform: scale(1); opacity: 1; }
}
@keyframes shake {
    0%,100% { transform: translateX(0); }
    20% { transform: translateX(-6px); }
    40% { transform: translateX(6px); }
    60% { transform: translateX(-4px); }
    80% { transform: translateX(4px); }
}
.stRadio > div {
    flex-direction: row !important;
    gap: 8px;
}
div.stButton > button {
    background: linear-gradient(135deg, #1e3a28, #152a1e) !important;
    border: 1.5px solid #2e5a3e !important;
    border-radius: 10px !important;
    color: #c8e6c9 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 10px 8px !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.3px !important;
    width: 100% !important;
}
div.stButton > button:hover {
    background: linear-gradient(135deg, #2e5a3e, #1e4a2e) !important;
    border-color: #4a9a5e !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(46,204,113,0.2) !important;
}
div.stButton > button:active {
    transform: translateY(0px) !important;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #27ae60, #1e8449) !important;
    border-color: #2ecc71 !important;
    color: white !important;
    font-size: 15px !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1a0f 0%, #080f0a 100%) !important;
    border-right: 1px solid #1a3020 !important;
}
[data-testid="stSidebar"] .stCheckbox label {
    color: #8ab89a !important;
    font-size: 12px !important;
}
@media (min-width: 768px) {
    [data-testid="stSidebar"] {
        width: 21rem !important;
    }
}
/* Responsive adjustments for Mobile */
@media (max-width: 768px) {
    [data-testid="stSidebar"] {
        width: 85vw !important;
    }
    /* Увеличение всех кнопок для удобного нажатия пальцем */
    div.stButton > button {
        padding: 18px 12px !important;
        font-size: 18px !important;
        margin-bottom: 8px !important;
        border-radius: 12px !important;
        min-height: 55px !important;
    }
    /* Перестроение радио-кнопок в вертикальный список */
    .stRadio > div {
        flex-direction: column !important;
        gap: 10px !important;
    }
    .stRadio label {
        background: rgba(42, 74, 50, 0.2);
        padding: 10px;
        border-radius: 8px;
        width: 100%;
    }
    /* Оптимизация карточек метрик */
    .metric-card {
        padding: 8px 10px !important;
        margin-bottom: 6px !important;
        border-radius: 10px !important;
    }
    .metric-value {
        font-size: 18px !important;
    }
    .metric-label {
        font-size: 8px !important;
        letter-spacing: 1px !important;
        margin-bottom: 2px !important;
    }
    /* Размер карт для мобильных */
    .playing-card {
        width: 60px;
        height: 80px;
        font-size: 22px;
    }
    .card-container {
        margin: 5px 0 !important;
    }
    .hand-badge {
        font-size: 15px;
        padding: 4px 12px;
    }
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #4a9a5e !important;
}
.result-summary {
    background: linear-gradient(135deg, #0f2a1a, #0a1f12);
    border: 2px solid #27ae60;
    border-radius: 20px;
    padding: 32px;
    text-align: center;
    margin: 16px 0;
}
.result-pct {
    font-size: 72px;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1;
    margin-bottom: 8px;
}
.grade-S { color: #f1c40f; }
.grade-A { color: #2ecc71; }
.grade-B { color: #3498db; }
.grade-C { color: #e67e22; }
.grade-D { color: #e74c3c; }
[data-testid="stExpander"] {
    background: #0f1f17 !important;
    border: 1px solid #1e3a28 !important;
    border-radius: 12px !important;
}
.section-title {
    color: #4a9a5e;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e3a28;
}
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #2a4a32, transparent);
    margin: 16px 0;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    'started': False, 'score': 0, 'total': 0,
    'error_mode': False, 'mode': 'spin',
    'test_mode': False, 'test_size': 20,
    'test_questions': [], 'test_idx': 0, 'test_results': [],
    'spin_config': {name: True for name in CHARTS.keys()},
    'hu_config': {name: True for name in HU_CHARTS.keys()},
    'current_spot': None, 'stack': 10,
    'cards': None, 'notation': None, 'error_mode': False, 'last_wrong': None,
    'streak': 0, 'best_streak': 0,
    'show_result': None,
    'mistake_history': [],
    'answered': False,
    'error_practice_mode': False, 'practice_error': None, 'practice_answer': None,
    'show_solution': False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

is_hu_mode = st.session_state.mode == 'hu'

def next_hand():
    is_hu = st.session_state.mode == 'hu'
    config = st.session_state.hu_config if is_hu else st.session_state.spin_config
    active_spots = [name for name, active in config.items() if active]
    if not active_spots:
        st.session_state.current_spot = None
        return
    if st.session_state.mistake_history and random.random() < 0.3:
        valid_mistakes = [m for m in st.session_state.mistake_history if m['spot'] in active_spots]
        if valid_mistakes:
            mistake = random.choice(valid_mistakes)
            deck = list(itertools.product(RANKS, SUITS))
            for _ in range(500):
                cards = random.sample(deck, 2)
                if get_hand_notation(cards[0], cards[1]) == mistake['hand']:
                    st.session_state.current_spot = mistake['spot']
                    st.session_state.stack = get_stack_for_spot(mistake['spot'])
                    st.session_state.cards = cards
                    st.session_state.notation = mistake['hand']
                    st.session_state.error_mode = False
                    st.session_state.answered = False
                    st.session_state.show_result = None
                    return
    for _ in range(50):
        spot = random.choice(active_spots)
        _, notation, cards = pick_relevant_hand(spot, is_hu)
        if cards and notation:
            st.session_state.current_spot = spot
            st.session_state.stack = get_stack_for_spot(spot)
            st.session_state.cards = cards
            st.session_state.notation = notation
            st.session_state.error_mode = False
            st.session_state.answered = False
            st.session_state.show_result = None
            return
    st.session_state.current_spot = None

def build_test():
    is_hu = st.session_state.mode == 'hu'
    config = st.session_state.hu_config if is_hu else st.session_state.spin_config
    active_spots = [name for name, active in config.items() if active]
    questions = []
    attempts = 0
    while len(questions) < st.session_state.test_size and attempts < 2000:
        attempts += 1
        if not active_spots:
            break
        spot = random.choice(active_spots)
        _, notation, cards = pick_relevant_hand(spot, is_hu)
        if cards and notation:
            stack = get_stack_for_spot(spot)
            correct = get_correct_action(notation, stack, spot, is_hu)
            questions.append({'spot': spot, 'cards': cards, 'notation': notation, 'stack': stack, 'correct': correct})
    st.session_state.test_questions = questions
    st.session_state.test_idx = 0
    st.session_state.test_results = []

# ============================================================
# SIDEBAR (без изменений)
# ============================================================
with st.sidebar:
    st.markdown('<div style="color:#4a9a5e;font-size:20px;font-weight:700;margin-bottom:4px;">♠ Preflop Trainer</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#4a7a5a;font-size:11px;margin-bottom:16px;">Professional preflop training tool</div>', unsafe_allow_html=True)

    mode_choice = st.radio("Mode", ["Spin & Go", "Heads-Up (HU)", "📊 Analysis"],
                           index=2 if st.session_state.mode == 'analysis' else (0 if st.session_state.mode == 'spin' else 1),
                           horizontal=True)
    new_mode = 'spin' if mode_choice == "Spin & Go" else ('hu' if mode_choice == "Heads-Up (HU)" else 'analysis')
    if new_mode != st.session_state.mode:
        st.session_state.mode = new_mode
        st.session_state.started = False
        st.session_state.test_mode = False


    if st.session_state.mode == 'analysis':
        st.info("Upload your GG histories in the main area.")
    else:
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Training Mode</div>', unsafe_allow_html=True)

        train_mode = st.radio("Mode", ["🔄 Infinite","📝 Test (20 Q)"],
                              index=1 if st.session_state.test_mode else 0,
                              horizontal=True, label_visibility="collapsed")
        if "Test" in train_mode:
            st.session_state.test_mode = True
            st.session_state.test_size = st.select_slider("Questions", [10,15,20,25,30,50], value=st.session_state.test_size)
        else:
            st.session_state.test_mode = False

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Active Spots</div>', unsafe_allow_html=True)

        categories = HU_CATEGORIES if new_mode == 'hu' else SPIN_CATEGORIES
        config_key = 'hu_config' if new_mode == 'hu' else 'spin_config'
        config = st.session_state[config_key]

        for cat_name, spot_list in categories.items():
            valid_spots = [s for s in spot_list if s in config]
            if not valid_spots:
                continue
            with st.expander(f"**{cat_name}**", expanded=False):
                all_on = all(config[s] for s in valid_spots)
                select_all = st.checkbox(f"All {cat_name}", value=all_on, key=f"all_toggle_{cat_name}")
                if select_all != all_on:
                    for s in valid_spots:
                        config[s] = select_all
                        st.session_state[f"chk_{s}"] = select_all
                    st.rerun()

                for spot in valid_spots:
                    old_val = config.get(spot, True)
                    config[spot] = st.checkbox(spot, value=old_val, key=f"chk_{spot}")
                    if config[spot] != old_val:
                        st.session_state[f"all_toggle_{cat_name}"] = all(config[s] for s in valid_spots)
                        st.rerun()

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        active_count = sum(1 for v in config.values() if v)
        st.markdown(f'<div style="color:#6b9e7a;font-size:12px;margin-bottom:12px;">Active: {active_count} spot{"s" if active_count != 1 else ""}</div>', unsafe_allow_html=True)

        btn_label = "▶ Start Test" if st.session_state.test_mode else "▶ Start Training"
        if st.button(btn_label, use_container_width=True, type="primary"):
            st.session_state.started = True
            st.session_state.score = 0
            st.session_state.total = 0
            st.session_state.streak = 0
            st.session_state.best_streak = 0
            if st.session_state.test_mode:
                build_test()
            else:
                next_hand()
            st.rerun()

        if st.session_state.started and st.session_state.total > 0:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            acc = st.session_state.score / st.session_state.total * 100
            st.markdown(f'<div style="color:#e8f5e9;font-size:13px;font-weight:600;margin-bottom:4px;">Score: {st.session_state.score}/{st.session_state.total}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="progress-outer"><div class="progress-inner" style="width:{acc:.0f}%"></div></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color:#4a9a5e;font-size:11px;">{acc:.1f}% accuracy | 🔥 Streak: {st.session_state.streak}</div>', unsafe_allow_html=True)

# ============================================================
# MAIN AREA
# ============================================================
if st.session_state.mode == 'analysis':
    st.markdown('<div class="section-title">GGPoker Pure cEV & Preflop Analysis</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload GGPoker Hand Histories (.txt)", accept_multiple_files=True, type=['txt'])
    
    if uploaded_files:
        if st.button("🚀 Run Full Analysis", type="primary"):
            with st.spinner("Analyzing hands and calculating Pure cEV..."):
                overall_report = analyze_gg_histories(uploaded_files)

                # --- Overall Metrics ---
                st.markdown('<div class="section-title" style="margin-top:20px;">Overall Performance</div>', unsafe_allow_html=True)
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Total Pure cEV</div>
                        <div class="metric-value" style="color:{'#2ecc71' if overall_report['total_tournament_cev'] >= 0 else '#e74c3c'}; font-size: 24px;">{overall_report['total_tournament_cev']:+.0f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    avg_pure = overall_report['total_tournament_cev'] / overall_report['tournaments_processed_count']
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Pure cEV / Tourney</div>
                        <div class="metric-value" style="color:{'#2ecc71' if avg_pure >= 0 else '#e74c3c'}; font-size: 24px;">{avg_pure:+.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    avg_adj = overall_report['total_allin_adj_cev'] / overall_report['tournaments_processed_count']
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Adj. cEV / Tourney</div>
                        <div class="metric-value" style="color:{'#2ecc71' if avg_adj >= 0 else '#e74c3c'}; font-size: 24px;">{avg_adj:+.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    avg_fin = overall_report['total_finished_cev'] / overall_report['tournaments_finished_count'] if overall_report['tournaments_finished_count'] > 0 else 0
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">cEV / Finished</div>
                        <div class="metric-value" style="color:{'#2ecc71' if avg_fin >= 0 else '#e74c3c'}; font-size: 24px;">{avg_fin:+.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col5:
                    acc = (overall_report['total_correct_decisions'] / overall_report['total_decisions_verified'] * 100) if overall_report['total_decisions_verified'] > 0 else 0
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Preflop Accuracy</div>
                        <div class="metric-value" style="font-size: 24px;">{acc:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.success(f"Analysis complete for {overall_report['tournaments_processed_count']} tournaments!")
                if overall_report['total_decisions_verified'] > 0:
                    st.info(f"Verified {overall_report['total_decisions_verified']} preflop decisions.")

                # ===================================================
                # ERROR TEST MODE - интерактивный проход ошибок
                # ===================================================
                if overall_report['all_errors']:
                    st.markdown('<div class="section-title" style="margin-top:40px;">🎓 Error Training Mode</div>', unsafe_allow_html=True)
                    
                    # Инициализируем error test если не инициализирован
                    if 'error_test_mode' not in st.session_state:
                        st.session_state.error_test_mode = False
                        st.session_state.error_test_idx = 0
                        st.session_state.error_test_results = []
                        st.session_state.error_test_errors = overall_report['all_errors'].copy()
                    
                    total_errors = len(st.session_state.error_test_errors)
                    idx = st.session_state.error_test_idx
                    
                    if idx >= total_errors:
                        # ИТОГИ ТЕСТИРОВАНИЯ ОШИБОК
                        results = st.session_state.error_test_results
                        correct_count = sum(1 for r in results if r['correct'])
                        pct = correct_count / total_errors * 100 if total_errors > 0 else 0
                        
                        if pct >= 95: grade, grade_color = "S", "#2ecc71"
                        elif pct >= 85: grade, grade_color = "A", "#27ae60"
                        elif pct >= 70: grade, grade_color = "B", "#f39c12"
                        elif pct >= 55: grade, grade_color = "C", "#e67e22"
                        else: grade, grade_color = "D", "#e74c3c"
                        
                        col_res_l, col_res_c, col_res_r = st.columns([1, 2, 1])
                        with col_res_c:
                            st.markdown(f"""
                            <div style="text-align:center;padding:40px 20px;background:rgba(42,74,50,0.3);border:2px solid #4a9a5e;border-radius:20px;">
                                <div style="color:#6b9e7a;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:20px;">Error Training Complete</div>
                                <div style="font-size:60px;color:{grade_color};font-weight:800;margin-bottom:10px;">{pct:.0f}%</div>
                                <div style="color:#4a9a5e;font-size:14px;margin-bottom:8px;">Grade: <span style="font-size:36px;color:{grade_color};font-weight:800;">{grade}</span></div>
                                <div style="color:#a8d5b5;font-size:14px;margin-top:16px;">{correct_count} / {total_errors} errors corrected</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("")
                            st.markdown('<div style="color:#4a9a5e;font-size:13px;font-weight:700;margin:20px 0 12px;">Errors You Got Wrong:</div>', unsafe_allow_html=True)
                            wrong = [r for r in results if not r['correct']]
                            if not wrong:
                                st.success("🎉 Perfect! All errors corrected!")
                            else:
                                for r in wrong:
                                    st.markdown(f"""
                                    <div style="background:#2e1a1a;border:1px solid #e74c3c;border-radius:8px;padding:12px 16px;margin-bottom:8px;font-size:12px;">
                                        <div style="color:#a8d5b5;font-weight:700;margin-bottom:6px;">❌ {r['hero_cards']} @ {r['spot']} ({r['stack_bb']}BB)</div>
                                        <div style="color:#f5b7b1;font-size:11px;">You chose: <strong>{r['chosen']}</strong></div>
                                        <div style="color:#2ecc71;font-size:11px;">Correct was: <strong>{r['correct_action']}</strong></div>
                                    </div>
                                    """)
                            
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("🔄 Retry All Errors", use_container_width=True, type="primary", key="retry_errors"):
                                    st.session_state.error_test_idx = 0
                                    st.session_state.error_test_results = []
                                    st.rerun()
                            with col_btn2:
                                if st.button("➡️ Continue to Tournament Details", use_container_width=True, key="skip_errors"):
                                    pass
                    else:
                        # ТЕКУЩАЯ ОШИБКА В ТЕСТЕ
                        error = st.session_state.error_test_errors[idx]
                        progress_pct = idx / total_errors * 100
                        
                        st.markdown(f"""
                        <div style="margin-bottom:12px;">
                            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                                <span style="color:#6b9e7a;font-size:12px;font-weight:600;">Error {idx+1} / {total_errors}</span>
                                <span style="color:#4a9a5e;font-size:12px;font-weight:600;">
                                    {sum(1 for r in st.session_state.error_test_results if r['correct'])} correct
                                </span>
                            </div>
                            <div style="background:#0f1f17;border:1px solid #2a4a32;height:8px;border-radius:20px;overflow:hidden;">
                                <div style="background:linear-gradient(90deg,#4a9a5e,#2ecc71);height:100%;width:{progress_pct:.1f}%;transition:width 0.3s;border-radius:20px;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Карты и ситуация
                        col_err_info, col_err_cards, col_err_context = st.columns([1.5, 1.2, 1.5])
                        
                        # Парсим карты
                        hero_cards_str = error['hero_cards']
                        card1_rank = hero_cards_str[0]
                        card2_rank = hero_cards_str[1]
                        is_suited = len(hero_cards_str) == 3 and hero_cards_str[2] == 's'
                        suit1 = '♠'
                        suit2 = '♥' if is_suited else '♣'
                        
                        with col_err_info:
                            st.markdown(f"""
                            <div style="background:#1a2e22;border:1px solid #4a9a5e;border-radius:10px;padding:16px;">
                                <div style="color:#4a9a5e;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:8px;">Situation</div>
                                <div style="color:#a8d5b5;font-size:13px;font-weight:700;margin-bottom:12px;line-height:1.4;">
                                    {error['spot']}
                                </div>
                                <div style="border-top:1px solid #2a4a32;padding-top:8px;font-size:11px;">
                                    <div style="color:#6b9e7a;margin-bottom:6px;">📍 {error['position']}</div>
                                    <div style="color:#6b9e7a;margin-bottom:6px;">💰 {error['stack_bb']}BB</div>
                                    <div style="color:#6b9e7a;">vs {error['opponent_last_action']}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_err_cards:
                            suit1_class = "card-red" if suit1 in ['♥','♦'] else "card-black"
                            suit2_class = "card-red" if suit2 in ['♥','♦'] else "card-black"
                            st.markdown(f"""
                            <div style="display:flex;flex-direction:column;align-items:center;gap:10px;">
                                <div class="card-container">
                                    <div class="playing-card {suit1_class}" style="font-size:40px;padding:12px;">{card1_rank}{suit1}</div>
                                    <div class="playing-card {suit2_class}" style="font-size:40px;padding:12px;">{card2_rank}{suit2}</div>
                                </div>
                                <div class="hand-badge">{hero_cards_str}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_err_context:
                            st.markdown(f"""
                            <div style="background:#1a2e22;border:1px solid #e74c3c;border-radius:10px;padding:16px;">
                                <div style="color:#e74c3c;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:8px;">Your Previous Action</div>
                                <div style="color:#f5b7b1;font-size:13px;font-weight:700;margin-bottom:12px;">
                                    {error['hero_action']}
                                </div>
                                <div style="border-top:1px solid #3a2a2a;padding-top:8px;font-size:11px;">
                                    <div style="color:#f5b7b1;margin-bottom:6px;">❌ This was incorrect</div>
                                    <div style="color:#e74c3c;margin-bottom:4px;font-weight:700;">Choose correctly now!</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Выбор действия
                        st.markdown("---")
                        st.markdown('<div style="color:#a8d5b5;font-size:13px;font-weight:700;margin-bottom:12px;text-align:center;">What should be the correct action?</div>', unsafe_allow_html=True)
                        
                        # Получаем возможные действия из чарта
                        is_hu = st.session_state.mode == 'hu'
                        charts_src = HU_CHARTS if is_hu else CHARTS
                        possible_actions = []
                        if error['spot'] in charts_src:
                            chart_data = charts_src[error['spot']]
                            if isinstance(chart_data.get('buttons'), list):
                                possible_actions = chart_data['buttons']
                        
                        if not possible_actions:
                            possible_actions = [error['correct_action'], error['hero_action'], 'All in', 'Call', 'Fold', 'Raise']
                            possible_actions = list(set(possible_actions))
                        
                        shuffled_actions = possible_actions.copy()
                        random.shuffle(shuffled_actions)
                        
                        n_cols = min(2, len(shuffled_actions))
                        cols = st.columns(n_cols)
                        
                        for i, action in enumerate(shuffled_actions):
                            with cols[i % n_cols]:
                                if st.button(action, use_container_width=True, key=f"err_action_{idx}_{i}", help=f"Error {idx+1}"):
                                    is_correct = action.lower() == error['correct_action'].lower()
                                    st.session_state.error_test_results.append({
                                        'hero_cards': error['hero_cards'],
                                        'spot': error['spot'],
                                        'stack_bb': error['stack_bb'],
                                        'chosen': action,
                                        'correct_action': error['correct_action'],
                                        'correct': is_correct,
                                        'opponent_last_action': error['opponent_last_action'],
                                        'position': error['position'],
                                        'hand_pure_ev': error['hand_pure_ev'],
                                        'hand_net_result': error['hand_net_result']
                                    })
                                    st.session_state.error_test_idx += 1
                                    st.rerun()

                # --- Tournament Details ---
                st.markdown('<div class="section-title" style="margin-top:40px;">📊 Tournament Details</div>', unsafe_allow_html=True)
                for t_report in overall_report['tournament_reports']:
                    with st.expander(f"**{t_report['file_name']}** (Finished: {'Yes' if t_report['tournament_finished'] else 'No'})", expanded=False):
                        st.markdown(f"**Starting Stack:** {t_report['starting_stack']} chips")
                        st.markdown(f"**Final Stack:** {t_report['final_stack']} chips")
                        st.markdown(f"**Real Chip Result:** {t_report['real_chip_result']:+} chips")
                        st.markdown(f"**Tournament cEV (Pure Preflop):** {t_report['tournament_cev']:+.1f} chips")
                        st.markdown(f"**All-in Adjusted cEV:** {t_report['allin_adj_cev']:+.1f} chips")
                        st.markdown(f"**Hands Processed:** {t_report['hands_processed']}")
                        st.markdown(f"**Preflop Decisions Verified:** {t_report['decisions_verified']}")
                        if t_report['decisions_verified'] > 0:
                            acc_t = (t_report['correct_decisions'] / t_report['decisions_verified'] * 100)
                            st.markdown(f"**Preflop Accuracy:** {acc_t:.1f}%")

                        if t_report['all_in_details']:
                            st.markdown("---")
                            st.markdown("**All-in Details:**")
                            all_in_df = pd.DataFrame(t_report['all_in_details'])
                            st.dataframe(all_in_df, use_container_width=True)
                        else:
                            st.info("No preflop all-in showdowns recorded.")

                # --- INTERACTIVE ERROR REVIEW ---
                if overall_report['all_errors']:
                    st.markdown('<div class="section-title" style="margin-top:40px;">🔍 Interactive Error Review</div>', unsafe_allow_html=True)
                    
                    # Фильтры
                    col_filter1, col_filter2, col_filter3 = st.columns(3)
                    with col_filter1:
                        filter_position = st.multiselect("Filter by Position:", 
                            options=sorted(set(e['position'] for e in overall_report['all_errors'])),
                            default=None,
                            key="error_pos_filter")
                    with col_filter2:
                        filter_spot = st.multiselect("Filter by Situation:", 
                            options=sorted(set(e['spot'] for e in overall_report['all_errors'])),
                            default=None,
                            key="error_spot_filter")
                    with col_filter3:
                        filter_stack_min = st.number_input("Min Stack (BB):", value=0.0, step=0.5)
                        filter_stack_max = st.number_input("Max Stack (BB):", value=100.0, step=0.5)
                    
                    # Применяем фильтры
                    filtered_errors = overall_report['all_errors']
                    if filter_position:
                        filtered_errors = [e for e in filtered_errors if e['position'] in filter_position]
                    if filter_spot:
                        filtered_errors = [e for e in filtered_errors if e['spot'] in filter_spot]
                    filtered_errors = [e for e in filtered_errors if filter_stack_min <= e['stack_bb'] <= filter_stack_max]
                    
                    st.info(f"Showing {len(filtered_errors)} of {len(overall_report['all_errors'])} errors")
                    
                    # Интерактивный просмотр ошибок
                    if filtered_errors:
                        error_idx = st.selectbox(
                            "Select an error to review:",
                            options=range(len(filtered_errors)),
                            format_func=lambda i: f"Hand #{filtered_errors[i]['hand_id']} | {filtered_errors[i]['hero_cards']} @ {filtered_errors[i]['position']} ({filtered_errors[i]['stack_bb']}BB)"
                        )
                        
                        error = filtered_errors[error_idx]
                        
                        st.markdown("---")
                        st.markdown(f"## Hand Details")
                        
                        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                        with col_info1:
                            st.metric("Hand", error['hero_cards'])
                        with col_info2:
                            st.metric("Position", error['position'])
                        with col_info3:
                            st.metric("Stack", f"{error['stack_bb']}BB")
                        with col_info4:
                            st.metric("Situation", error['spot'][:20] + "..." if len(error['spot']) > 20 else error['spot'])
                        
                        col_action1, col_action2 = st.columns(2)
                        with col_action1:
                            st.markdown(f"""
                            <div style="background:#1a2e22;border:2px solid #4a9a5e;border-radius:8px;padding:16px;">
                                <div style="color:#4a9a5e;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">✓ Correct Action</div>
                                <div style="color:#a8d5b5;font-size:18px;font-weight:700;">{error['correct_action']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_action2:
                            hero_action_display = error['hero_action']
                            if error['is_allin']:
                                hero_action_display += " (ALL-IN)"
                            st.markdown(f"""
                            <div style="background:#2e1a1a;border:2px solid #e74c3c;border-radius:8px;padding:16px;">
                                <div style="color:#e74c3c;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">✗ Your Action</div>
                                <div style="color:#f5b7b1;font-size:18px;font-weight:700;">{hero_action_display}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown("## Context")
                        
                        col_context1, col_context2, col_context3 = st.columns(3)
                        with col_context1:
                            result_color = "#2ecc71" if error['hand_net_result'] >= 0 else "#e74c3c"
                            st.markdown(f"""
                            <div style="background:#1a2e22;border:1px solid {result_color};border-radius:8px;padding:12px;text-align:center;">
                                <div style="color:#a8d5b5;font-size:11px;font-weight:700;">Hand Result</div>
                                <div style="color:{result_color};font-size:20px;font-weight:700;">{error['hand_net_result']:+d}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_context2:
                            ev_color = "#2ecc71" if error['hand_pure_ev'] >= 0 else "#e74c3c"
                            st.markdown(f"""
                            <div style="background:#1a2e22;border:1px solid {ev_color};border-radius:8px;padding:12px;text-align:center;">
                                <div style="color:#a8d5b5;font-size:11px;font-weight:700;">Pure EV</div>
                                <div style="color:{ev_color};font-size:20px;font-weight:700;">{error['hand_pure_ev']:+.1f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_context3:
                            st.markdown(f"""
                            <div style="background:#1a2e22;border:1px solid #3498db;border-radius:8px;padding:12px;text-align:center;">
                                <div style="color:#a8d5b5;font-size:11px;font-weight:700;">Tournament</div>
                                <div style="color:#3498db;font-size:12px;font-weight:700;overflow:hidden;text-overflow:ellipsis;">{error['tournament'][-20:]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Заметки о ситуации
                        st.markdown("**Analysis Notes:**")
                        st.write(f"In {error['spot']}, after opponent's {error['opponent_last_action']}, the correct play is **{error['correct_action']}**, but you played **{error['hero_action']}**{'(all-in)' if error['is_allin'] else ''}.")
                        
                        # Место для своих заметок
                        st.text_area("Your Notes:", placeholder="Write down what you learned or why this was a mistake...", key=f"notes_{error['hand_id']}")
                        
                        # ПРАКТИКА НА ДАННОЙ ОШИБКЕ
                        st.markdown("---")
                        st.markdown("## 📚 Practice This Hand")
                        
                        col_practice1, col_practice2 = st.columns([1, 1])
                        with col_practice1:
                            if st.button("🎯 Try Again (Test Mode)", use_container_width=True, type="primary", key=f"practice_{error['hand_id']}"):
                                st.session_state.error_practice_mode = True
                                st.session_state.practice_error = error
                                st.session_state.practice_answer = None
                                st.rerun()
                        
                        with col_practice2:
                            if st.button("📖 Show Me the Solution", use_container_width=True, key=f"solution_{error['hand_id']}"):
                                st.session_state.show_solution = True
                        
                        # Показываем решение если нажали кнопку
                        if st.session_state.get('show_solution', False) and st.session_state.get('practice_error') == error:
                            st.markdown("---")
                            st.markdown("### 💡 Solution Explanation")
                            st.info(f"""
                            **Why {error['correct_action']} was the correct play:**
                            
                            • **Position:** {error['position']} 
                            • **Stack Depth:** {error['stack_bb']}BB
                            • **Situation:** {error['spot']}
                            
                            **Key concepts:**
                            1. At {error['stack_bb']}BB in {error['position']}, stack depth dictates range
                            2. Against opponent's {error['opponent_last_action']}, the best response is {error['correct_action']}
                            3. Your play ({error['hero_action']}) was suboptimal and cost you EV
                            
                            **Hand Outcome:**
                            - Hand Result: {error['hand_net_result']:+d} chips
                            - Pure EV: {error['hand_pure_ev']:+.1f} chips
                            - Difference: {(error['hand_net_result'] - error['hand_pure_ev']):+.1f} chips
                            """)
                    else:
                        st.info("No errors match the selected filters.")
                
                # РЕЖИМ ПРАКТИКИ НА ОШИБКЕ
                if st.session_state.get('error_practice_mode', False) and st.session_state.get('practice_error'):
                    error = st.session_state.practice_error
                    st.markdown("---")
                    st.markdown("## 🎯 Error Practice Mode")
                    st.info("Try to choose the correct action for this hand you got wrong.")
                    
                    # Парсим карточки из hero_cards (e.g. "AKs" -> две карточки)
                    hero_cards_str = error['hero_cards']
                    card1_rank = hero_cards_str[0]
                    card2_rank = hero_cards_str[1]
                    
                    # Определяем масти на основе suited/offsuit
                    if len(hero_cards_str) == 3:  # e.g., "AKs"
                        is_suited = hero_cards_str[2] == 's'
                    else:  # "AKo" или 2 символа
                        is_suited = False
                    
                    suit1 = '♠'
                    suit2 = '♥' if is_suited else '♣'
                    
                    card1 = f"{card1_rank}{suit1}"
                    card2 = f"{card2_rank}{suit2}"
                    
                    # Отображаем карточки в большом формате
                    col_info1, col_cards_prac, col_info2 = st.columns([1.5, 1, 1.5])
                    
                    with col_info1:
                        st.markdown(f"""
                        <div style="background:#1a2e22;border:1px solid #4a9a5e;border-radius:8px;padding:16px;">
                            <div style="color:#4a9a5e;font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:8px;">Situation</div>
                            <div style="color:#a8d5b5;font-size:14px;font-weight:700;margin-bottom:12px;">{error['spot']}</div>
                            <div style="color:#6b9e7a;font-size:12px;">Position: {error['position']}</div>
                            <div style="color:#6b9e7a;font-size:12px;">Stack: {error['stack_bb']}BB</div>
                            <div style="color:#6b9e7a;font-size:12px;margin-top:8px;">vs {error['opponent_last_action']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_cards_prac:
                        suit1_color = "red" if suit1 in ['♥','♦'] else "black"
                        suit2_color = "red" if suit2 in ['♥','♦'] else "black"
                        suit1_class = "card-red" if suit1_color == "red" else "card-black"
                        suit2_class = "card-red" if suit2_color == "red" else "card-black"
                        
                        st.markdown(f"""
                        <div style="display:flex;flex-direction:column;align-items:center;gap:12px;">
                            <div class="card-container">
                                <div class="playing-card {suit1_class}" style="font-size:48px;padding:20px;">{card1}</div>
                                <div class="playing-card {suit2_class}" style="font-size:48px;padding:20px;">{card2}</div>
                            </div>
                            <div class="hand-badge" style="font-size:18px;">{hero_cards_str}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_info2:
                        st.markdown(f"""
                        <div style="background:#1a2e22;border:1px solid #e74c3c;border-radius:8px;padding:16px;">
                            <div style="color:#e74c3c;font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:8px;">Your Previous Action</div>
                            <div style="color:#f5b7b1;font-size:14px;font-weight:700;margin-bottom:12px;">{error['hero_action']}</div>
                            <div style="color:#d4b5b1;font-size:12px;">❌ This was incorrect</div>
                            <div style="color:#d4b5b1;font-size:12px;margin-top:8px;">Try again!</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.markdown("### Choose the Correct Action:")
                    
                    # Получаем правильные действия из чартов
                    correct_actions_list = error['correct_action'].split('/')
                    
                    # Создаём кнопки для каждого действия
                    # Генерируем список возможных действий из чарта для этого спота
                    is_hu = st.session_state.mode == 'hu'
                    charts_src = HU_CHARTS if is_hu else CHARTS
                    
                    possible_actions = []
                    if error['spot'] in charts_src:
                        chart_data = charts_src[error['spot']]
                        if isinstance(chart_data.get('buttons'), list):
                            possible_actions = chart_data['buttons']
                    
                    if not possible_actions:
                        possible_actions = [error['correct_action'], error['hero_action'], 'All in', 'Call', 'Fold', 'Raise']
                        possible_actions = list(set(possible_actions))  # Удаляем дубликаты
                    
                    # Перетасовываем действия
                    shuffled_actions = possible_actions.copy()
                    random.shuffle(shuffled_actions)
                    
                    # Показываем кнопки действий в 2 колонки
                    n_cols = min(2, len(shuffled_actions))
                    cols = st.columns(n_cols)
                    
                    for i, action in enumerate(shuffled_actions):
                        with cols[i % n_cols]:
                            if st.button(action, use_container_width=True, key=f"practice_action_{i}_{error['hand_id']}"):
                                st.session_state.practice_answer = action
                                st.rerun()
                    
                    # Показываем результат если пользователь выбрал действие
                    if st.session_state.get('practice_answer'):
                        chosen = st.session_state.practice_answer
                        is_correct = chosen.lower() == error['correct_action'].lower()
                        
                        st.markdown("---")
                        
                        if is_correct:
                            st.success(f"✅ Correct! The right action was **{error['correct_action']}**")
                            st.markdown(f"""
                            **Explanation:**
                            - You recognized that {error['correct_action']} was the proper play
                            - This hand had EV of {error['hand_pure_ev']:+.1f} chips
                            - The outcome was {error['hand_net_result']:+d} chips
                            """)
                        else:
                            st.error(f"❌ Incorrect! You chose **{chosen}**, but the correct action was **{error['correct_action']}**")
                            st.markdown(f"""
                            **Why your choice was wrong:**
                            - **Your action:** {chosen}
                            - **Correct action:** {error['correct_action']}
                            - **Position:** {error['position']}
                            - **Stack:** {error['stack_bb']}BB in {error['spot']}
                            - **Against:** {error['opponent_last_action']}
                            
                            **Hand Metrics:**
                            - EV of correct play: {error['hand_pure_ev']:+.1f} chips
                            - Actual outcome: {error['hand_net_result']:+d} chips
                            """)
                        
                        # Кнопки для продолжения
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        with col_btn1:
                            if st.button("🔄 Try Different Error", use_container_width=True):
                                st.session_state.error_practice_mode = False
                                st.session_state.practice_error = None
                                st.session_state.practice_answer = None
                                st.rerun()
                        with col_btn2:
                            if st.button("🔁 Try This Again", use_container_width=True):
                                st.session_state.practice_answer = None
                                st.rerun()
                        with col_btn3:
                            if st.button("📊 Back to Error Review", use_container_width=True, type="primary"):
                                st.session_state.error_practice_mode = False
                                st.session_state.practice_error = None
                                st.session_state.practice_answer = None
                                st.rerun()
    else:
        st.markdown("""
        <div style="padding:40px; text-align:center; background:rgba(255,255,255,0.03); border-radius:20px; border: 1px dashed #2e5a3e;">
            <div style="font-size:48px; margin-bottom:20px;">📂</div>
            <div style="color:#a8d5b5; font-size:16px;">Drop your GGPoker text files here to see your performance.</div>
        </div>
        """, unsafe_allow_html=True)

elif not st.session_state.started:
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:64px;margin-bottom:16px;">🃏</div>
            <div style="color:#e8f5e9;font-size:32px;font-weight:700;margin-bottom:8px;">Preflop Trainer Pro</div>
            <div style="color:#6b9e7a;font-size:14px;margin-bottom:32px;">Master preflop decisions for Spin & Go and Heads-Up</div>
            <div style="background:linear-gradient(135deg,#1a2e22,#0f1f17);border:1px solid #2a4a32;border-radius:16px;padding:24px;text-align:left;margin-bottom:24px;">
                <div style="color:#4a9a5e;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">Features</div>
                <div style="color:#a8d5b5;font-size:13px;line-height:2;">
                ♠ Spin & Go charts (13-16bb, 10-13bb, &lt;10bb)<br>
                ♦ Full Heads-Up range charts<br>
                ♣ Infinite training or structured tests<br>
                ♥ Only relevant, borderline-interesting hands<br>
                ♠ Streak tracking & accuracy metrics
                </div>
            </div>
            <div style="color:#6b9e7a;font-size:12px;">← Configure your spots in the sidebar, then click <strong>Start Training</strong></div>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.test_mode:
    # TEST MODE (без изменений, но матрица будет отображаться через новый render)
    questions = st.session_state.test_questions
    idx = st.session_state.test_idx
    total_q = len(questions)

    if idx >= total_q:
        results = st.session_state.test_results
        correct_count = sum(1 for r in results if r['correct'])
        pct = correct_count / total_q * 100 if total_q > 0 else 0
        if pct >= 95: grade, grade_class = "S", "grade-S"
        elif pct >= 85: grade, grade_class = "A", "grade-A"
        elif pct >= 70: grade, grade_class = "B", "grade-B"
        elif pct >= 55: grade, grade_class = "C", "grade-C"
        else: grade, grade_class = "D", "grade-D"
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown(f"""
            <div class="result-summary">
                <div style="color:#6b9e7a;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">Test Complete</div>
                <div class="result-pct {grade_class}">{pct:.0f}%</div>
                <div style="color:#4a9a5e;font-size:14px;margin-top:8px;">Grade: <span class="{grade_class}" style="font-size:24px;font-weight:800;">{grade}</span></div>
                <div style="color:#a8d5b5;margin-top:16px;font-size:14px;">{correct_count} / {total_q} correct</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('<div style="color:#4a9a5e;font-size:13px;font-weight:700;margin:16px 0 8px;">Review incorrect answers</div>', unsafe_allow_html=True)
            wrong = [r for r in results if not r['correct']]
            if not wrong:
                st.markdown('<div style="color:#2ecc71;font-size:13px;">🎉 Perfect score! No mistakes.</div>', unsafe_allow_html=True)
            else:
                for r in wrong:
                    c1, c2 = r['cards']
                    s1_color = "red" if c1[1] in ['♥','♦'] else "black"
                    s2_color = "red" if c2[1] in ['♥','♦'] else "black"
                    st.markdown(f"""
                    <div style="background:#1a1a2a;border:1px solid #3a2a2a;border-radius:10px;padding:12px 16px;margin-bottom:8px;font-size:12px;">
                        <span style="font-family:monospace;font-weight:700;color:{'#e74c3c' if s1_color=='red' else '#ddd'}">{c1[0]}{c1[1]}</span>
                        <span style="font-family:monospace;font-weight:700;color:{'#e74c3c' if s2_color=='red' else '#ddd'}"> {c2[0]}{c2[1]}</span>
                        <span style="color:#888;margin:0 8px;">·</span>
                        <span style="color:#9b8;">{r['spot']}</span> ({r['stack']}bb)
                        <br>
                        <span style="color:#e74c3c;">✗ You: {r['chosen']}</span>
                        <span style="margin:0 8px;color:#444;">→</span>
                        <span style="color:#2ecc71;">✓ Correct: {r['correct_action']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Retry Test", use_container_width=True, type="primary"):
                    build_test()
                    st.rerun()
            with col2:
                if st.button("🆕 New Test", use_container_width=True):
                    build_test()
                    st.rerun()
    else:
        q = questions[idx]
        progress_pct = idx / total_q * 100
        st.markdown(f"""
        <div style="margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="color:#6b9e7a;font-size:12px;font-weight:600;">Question {idx+1} / {total_q}</span>
                <span style="color:#4a9a5e;font-size:12px;font-weight:600;">{st.session_state.score} correct</span>
            </div>
            <div class="progress-outer">
                <div class="progress-inner" style="width:{progress_pct:.1f}%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        col_info, col_cards = st.columns([3, 2])
        c1, c2 = q['cards']
        with col_info:
            st.markdown(f'<div class="spot-pill">📍 {q["spot"]}</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="metric-card" style="margin-top:8px;">
                <div class="metric-label">Stack</div>
                <div class="metric-value">{q["stack"]} <span style="font-size:18px;color:#4a9a5e;">BB</span></div>
            </div>
            """, unsafe_allow_html=True)
        with col_cards:
            suit1_class = "card-red" if c1[1] in ['♥','♦'] else "card-black"
            suit2_class = "card-red" if c2[1] in ['♥','♦'] else "card-black"
            st.markdown(f"""
            <div style="display:flex;flex-direction:column;align-items:center;gap:8px;padding-top:8px;">
                <div class="card-container">
                    <div class="playing-card {suit1_class}">{c1[0]}{c1[1]}</div>
                    <div class="playing-card {suit2_class}">{c2[0]}{c2[1]}</div>
                </div>
                <div class="hand-badge">{q["notation"]}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#a8d5b5;font-size:13px;font-weight:600;margin-bottom:10px;">Choose your action:</div>', unsafe_allow_html=True)
        is_hu = st.session_state.mode == 'hu'
        charts_src = HU_CHARTS if is_hu else CHARTS
        buttons = charts_src[q['spot']]['buttons']
        n_cols = min(3, len(buttons))
        cols = st.columns(n_cols)
        for i, btn in enumerate(buttons):
            with cols[i % n_cols]:
                if st.button(btn, key=f"test_btn_{idx}_{i}", use_container_width=True):
                    is_correct = btn == q['correct']
                    st.session_state.test_results.append({
                        'cards': q['cards'], 'notation': q['notation'],
                        'spot': q['spot'], 'stack': q['stack'],
                        'chosen': btn, 'correct_action': q['correct'],
                        'correct': is_correct
                    })
                    if is_correct:
                        st.session_state.score += 1
                    st.session_state.total += 1
                    st.session_state.test_idx += 1
                    st.rerun()

else:
    # INFINITE TRAINING MODE
    if not st.session_state.current_spot:
        st.warning("⚠️ No active spots. Enable some spots in the sidebar and click Start Training.")
        st.stop()

    is_hu = st.session_state.mode == 'hu'

    c1, c2 = st.session_state.cards
    suit1_class = "card-red" if c1[1] in ['♥','♦'] else "card-black"
    suit2_class = "card-red" if c2[1] in ['♥','♦'] else "card-black"

    # 1. Header: Spot and Stack (Compact)
    h_col1, h_col2 = st.columns([2, 1])
    with h_col1:
        st.markdown(f'<div class="spot-pill">📍 {st.session_state.current_spot}</div>', unsafe_allow_html=True)
    with h_col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Stack</div><div class="metric-value">{st.session_state.stack} BB</div></div>', unsafe_allow_html=True)

    # 2. Main Content: Cards (Centered)
    st.markdown(f"""
    <div style="display:flex;flex-direction:column;align-items:center;gap:8px;padding:5px 0;">
        <div class="card-container">
            <div class="playing-card {suit1_class}">{c1[0]}{c1[1]}</div>
            <div class="playing-card {suit2_class}">{c2[0]}{c2[1]}</div>
        </div>
        <div class="hand-badge">{st.session_state.notation}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    correct = get_correct_action(
        st.session_state.notation,
        st.session_state.stack,
        st.session_state.current_spot,
        is_hu=is_hu
    )
    charts_src = HU_CHARTS if is_hu else CHARTS

    if not st.session_state.answered:
        st.markdown('<div style="color:#a8d5b5;font-size:13px;font-weight:600;margin-bottom:10px;">Choose your action:</div>', unsafe_allow_html=True)
        buttons = charts_src[st.session_state.current_spot]["buttons"]
        n_cols = min(3, len(buttons))
        cols = st.columns(n_cols)
        for i, btn in enumerate(buttons):
            with cols[i % n_cols]:
                if st.button(btn, key=f"inf_btn_{btn}_{i}", use_container_width=True):
                    st.session_state.total += 1
                    st.session_state.answered = True
                    if btn == correct:
                        st.session_state.score += 1
                        st.session_state.streak += 1
                        st.session_state.show_result = 'correct'
                        if st.session_state.streak > st.session_state.best_streak:
                            st.session_state.best_streak = st.session_state.streak
                        st.rerun()
                    else:
                        st.session_state.streak = 0
                        st.session_state.show_result = 'wrong'
                        st.session_state.last_wrong = btn
                        st.session_state.mistake_history.append({
                            'hand': st.session_state.notation,
                            'spot': st.session_state.current_spot
                        })
                        st.rerun()
    else:
        if st.session_state.show_result == 'correct':
            st.markdown(f"""
            <div class="banner-correct">
                ✓ Correct: <strong>{correct}</strong>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="banner-wrong">
                <span style="font-size: 14px; opacity: 0.8;">Action Error</span><br>
                <span style="color: #ff7675;">✗ {st.session_state.last_wrong}</span> 
                <span style="margin: 0 10px; opacity: 0.5;">→</span>
                <span style="color: #55efc4;">✓ {correct}</span>
            </div>
            """, unsafe_allow_html=True)

        if st.button("➡ Next Hand", use_container_width=True, type="primary"):
            next_hand()
            st.rerun()

    # 4. Footer: Secondary Stats (Smaller, at the bottom)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        acc = (st.session_state.score / st.session_state.total * 100) if st.session_state.total > 0 else 0
        st.markdown(f'<div class="metric-card"><div class="metric-label">Acc</div><div class="metric-value">{acc:.0f}%</div></div>', unsafe_allow_html=True)
    with f_col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Streak</div><div class="metric-value">{st.session_state.streak}</div></div>', unsafe_allow_html=True)
    with f_col3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Best</div><div class="metric-value">{st.session_state.best_streak}</div></div>', unsafe_allow_html=True)
    with f_col4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total</div><div class="metric-value">{st.session_state.total}</div></div>', unsafe_allow_html=True)

        with st.expander("📊 View chart data for this spot", expanded=True):
            chart_data = charts_src[st.session_state.current_spot]["data"]
            st.markdown(f"**Hand:** `{st.session_state.notation}` · **Spot:** {st.session_state.current_spot} · **Stack:** {st.session_state.stack}bb")
            for action, hands in chart_data.items():
                if hands == "EVERYTHING_ELSE":
                    continue
                if isinstance(hands, list) and st.session_state.notation in hands:
                    st.markdown(f"✅ `{st.session_state.notation}` belongs to: **{action}**")
                    break

        st.markdown('<div class="section-title">Range Chart</div>', unsafe_allow_html=True)
        # Генерируем имя файла из названия спота
        safe_name = st.session_state.current_spot.replace(" ", "_").replace("<", "lt")
        img_path = os.path.join("img", f"{safe_name}.jpg")
        
        if os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        else:
            st.info(f"Скриншот чарта для '{st.session_state.current_spot}' пока не добавлен в папку /img.")