"""Thread-safe in-memory domain storage and state manager."""
import copy
import threading
from typing import Any, Dict, List, Optional
from app.errors import AppException


class StateManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.seed: int = 42
        self.tenants: List[str] = ["tenant-alpha", "tenant-beta"]
        self.sports: Dict[str, Dict[str, Any]] = {}
        self.leagues: Dict[str, Dict[str, Any]] = {}
        self.matches: Dict[str, Dict[str, Any]] = {}
        self.match_events: Dict[str, List[Dict[str, Any]]] = {}
        self.event_responses: Dict[str, Dict[str, Any]] = {}  # event_id -> {body, response}
        
        # Store & Inventory
        self.products: Dict[str, Dict[str, Any]] = {}
        self.variants: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}  # order_id -> {body, response}
        
        # Roster
        self.roster_leagues: Dict[str, Dict[str, Any]] = {}
        self.players: Dict[str, Dict[str, Any]] = {}
        self.squads: Dict[str, Dict[str, Any]] = {}
        self.roster_history: Dict[str, List[Dict[str, Any]]] = {}  # player_id -> list of audit entries
        self.transfer_responses: Dict[str, Dict[str, Any]] = {}  # request_id -> {body, response}
        self.audit_counter = 0

        # Offline sync
        self.offline_actions: Dict[str, Dict[str, Any]] = {}  # f"{device_id}:{action_id}" -> result

        # Seed baseline at init
        self.reset(seed=42, stock={"var-jersey-001-M": 1, "var-jersey-001-L": 5})

    def next_audit_id(self) -> str:
        self.audit_counter += 1
        return f"au-{self.audit_counter:04d}"

    def reset(self, seed: int = 42, stock: Optional[Dict[str, int]] = None):
        with self.lock:
            self.seed = seed
            stock = stock or {"var-jersey-001-M": 1, "var-jersey-001-L": 5}
            m_stock = stock.get("var-jersey-001-M", 1)
            l_stock = stock.get("var-jersey-001-L", 5)

            self.tenants = ["tenant-alpha", "tenant-beta"]
            self.leagues.clear()
            self.matches.clear()
            self.match_events.clear()
            self.event_responses.clear()
            self.orders.clear()
            self.roster_leagues.clear()
            self.players.clear()
            self.squads.clear()
            self.roster_history.clear()
            self.transfer_responses.clear()
            self.offline_actions.clear()
            self.audit_counter = 0

            # Store baseline
            self.products = {
                "prod-jersey-001": {
                    "product_id": "prod-jersey-001",
                    "tenant_id": "tenant-alpha",
                    "name": "Official Jersey 2026",
                }
            }
            self.variants = {
                "var-jersey-001-M": {
                    "variant_id": "var-jersey-001-M",
                    "product_id": "prod-jersey-001",
                    "price_minor": 450000,
                    "currency": "PKR",
                    "stock": m_stock,
                    "reserved": 0,
                },
                "var-jersey-001-L": {
                    "variant_id": "var-jersey-001-L",
                    "product_id": "prod-jersey-001",
                    "price_minor": 450000,
                    "currency": "PKR",
                    "stock": l_stock,
                    "reserved": 0,
                },
            }

            # Seed the 4 baseline sports
            self.sports = {
                "football": {
                    "sport_id": "football",
                    "name": "Football",
                    "scoring_model": "event",
                    "periods": {"count": 2, "duration_minutes": 45},
                    "scoring_events": {"goal": {"points": 1}},
                    "draw_allowed": True,
                    "overtime": {"policy": "none"},
                    "tie_break_order": ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"],
                    "roster": {
                        "min_squad_size": 11,
                        "max_squad_size": 25,
                        "required_positions": {"gk": 1},
                    },
                },
                "basketball": {
                    "sport_id": "basketball",
                    "name": "Basketball",
                    "scoring_model": "event",
                    "periods": {"count": 4, "duration_minutes": 12},
                    "scoring_events": {
                        "free_throw": {"points": 1},
                        "two_pointer": {"points": 2},
                        "three_pointer": {"points": 3},
                    },
                    "draw_allowed": False,
                    "overtime": {"policy": "extra_time", "duration_minutes": 5},
                    "tie_break_order": ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"],
                    "roster": {
                        "min_squad_size": 5,
                        "max_squad_size": 15,
                        "required_positions": {},
                    },
                },
                "cricket": {
                    "sport_id": "cricket",
                    "name": "Cricket",
                    "scoring_model": "innings",
                    "periods": {
                        "innings_per_team": 1,
                        "overs_per_innings": 20,
                        "balls_per_over": 6,
                        "wickets_per_innings": 10,
                    },
                    "scoring_events": {
                        "dot_ball": {"runs": 0, "legal_ball": True, "wicket": False},
                        "single": {"runs": 1, "legal_ball": True, "wicket": False},
                        "two": {"runs": 2, "legal_ball": True, "wicket": False},
                        "four": {"runs": 4, "legal_ball": True, "wicket": False},
                        "six": {"runs": 6, "legal_ball": True, "wicket": False},
                        "wide": {"runs": 1, "legal_ball": False, "wicket": False},
                        "no_ball": {"runs": 1, "legal_ball": False, "wicket": False},
                        "wicket": {"runs": 0, "legal_ball": True, "wicket": True},
                    },
                    "draw_allowed": True,
                    "overtime": {"policy": "super_over"},
                    "tie_break_order": ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"],
                    "roster": {
                        "min_squad_size": 11,
                        "max_squad_size": 18,
                        "required_positions": {"wicketkeeper": 1},
                    },
                },
                "esports": {
                    "sport_id": "esports",
                    "name": "Esports",
                    "scoring_model": "round",
                    "periods": {"best_of": 3},
                    "scoring_events": {"round_win": {"rounds": 1}},
                    "draw_allowed": False,
                    "overtime": {"policy": "none"},
                    "tie_break_order": ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"],
                    "roster": {
                        "min_squad_size": 5,
                        "max_squad_size": 8,
                        "required_positions": {},
                    },
                },
            }

            # Seed RBAC scenario
            # Leagues
            self.leagues["league-alpha-1"] = {
                "league_id": "league-alpha-1",
                "tenant_id": "tenant-alpha",
                "sport_id": "football",
                "teams": ["club-alpha-1", "club-alpha-2"],
                "fixtures": [],
                "points": {"win": 3, "draw": 1, "loss": 0},
                "tie_break_order": ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"],
                "qualification": {"spots": 1},
                "lots_seed": seed,
            }
            self.leagues["league-alpha-2"] = {
                "league_id": "league-alpha-2",
                "tenant_id": "tenant-alpha",
                "sport_id": "football",
                "teams": ["club-alpha-1", "club-alpha-2"],
                "fixtures": [],
                "points": {"win": 3, "draw": 1, "loss": 0},
                "tie_break_order": ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"],
                "qualification": {"spots": 1},
                "lots_seed": seed,
            }
            self.leagues["league-beta-1"] = {
                "league_id": "league-beta-1",
                "tenant_id": "tenant-beta",
                "sport_id": "football",
                "teams": ["club-beta-1"],
                "fixtures": [],
                "points": {"win": 3, "draw": 1, "loss": 0},
                "tie_break_order": ["h2h_points", "h2h_diff", "overall_diff", "scored", "fair_play", "draw_lots"],
                "qualification": {"spots": 1},
                "lots_seed": seed,
            }

            # Clubs
            self.squads["club-alpha-1"] = {
                "club_id": "club-alpha-1",
                "tenant_id": "tenant-alpha",
                "name": "Alpha Club 1",
            }
            self.squads["club-alpha-2"] = {
                "club_id": "club-alpha-2",
                "tenant_id": "tenant-alpha",
                "name": "Alpha Club 2",
            }
            self.squads["club-beta-1"] = {
                "club_id": "club-beta-1",
                "tenant_id": "tenant-beta",
                "name": "Beta Club 1",
            }

            # Players
            self.players["player-alpha-1"] = {
                "player_id": "player-alpha-1",
                "club_id": "club-alpha-1",
                "tenant_id": "tenant-alpha",
                "name": "Alpha Player 1",
            }
            self.players["player-alpha-2"] = {
                "player_id": "player-alpha-2",
                "club_id": "club-alpha-2",
                "tenant_id": "tenant-alpha",
                "name": "Alpha Player 2",
            }
            self.players["player-beta-1"] = {
                "player_id": "player-beta-1",
                "club_id": "club-beta-1",
                "tenant_id": "tenant-beta",
                "name": "Beta Player 1",
            }

            return {
                "status": "reset_complete",
                "seed": seed,
                "sports": ["football", "basketball", "cricket", "esports"],
                "tenants": ["tenant-alpha", "tenant-beta"],
                "stock": {
                    "var-jersey-001-M": m_stock,
                    "var-jersey-001-L": l_stock,
                },
            }


state = StateManager()
