"use client";

import { useEffect, useState, useRef } from "react";
import Nav from "@/components/Nav/Nav";
import ConditionalFooter from "@/components/ConditionalFooter/ConditionalFooter";
import { useUser } from "@/lib/hooks";
import fetchApi from "@/lib/api";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import SakuraPetals from "@/components/SakuraPetals/SakuraPetals";
import "./leaderboard.css";

const LeaderboardPage = () => {
  const { user } = useUser();
  const [leaderboard, setLeaderboard] = useState([]);
  const [userRank, setUserRank] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const gridRef = useRef(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await fetchApi("/auth/leaderboard/");
        if (data && Array.isArray(data)) {
          setLeaderboard(data);
        }

        if (user) {
          try {
            const usersAbove = leaderboard.filter(u => u.loyalty_points > (user.loyalty_points || 0)).length;
            setUserRank(usersAbove + 1);
          } catch (err) {
            console.error("Failed to calculate rank:", err);
          }
        }
      } catch (error) {
        console.error("Failed to fetch leaderboard:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [user]);

  // Recalculate user rank when leaderboard loads
  useEffect(() => {
    if (user && leaderboard.length > 0) {
      const usersAbove = leaderboard.filter(u => u.loyalty_points > (user.loyalty_points || 0)).length;
      setUserRank(usersAbove + 1);
    }
  }, [leaderboard, user]);

  useGSAP(() => {
    if (gridRef.current) {
      gsap.fromTo(
        gridRef.current.querySelectorAll(".leaderboard-card"),
        { y: 35, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.9, stagger: 0.05, ease: "power3.out", delay: 0.2 }
      );
    }
  }, { scope: gridRef });

  const getRankBadge = (rank) => {
    if (rank === 1) return "🥇";
    if (rank === 2) return "🥈";
    if (rank === 3) return "🥉";
    return `#${rank}`;
  };

  return (
    <>
      <SakuraPetals />
      <div className="page leaderboard-page">
        <div className="container">
          <div className="leaderboard-hero">
            <h1>Leaderboard</h1>
            <p>Top collectors competing for the ultimate fan status</p>
            {user && userRank && (
              <div className="user-rank-badge">
                <span className="rank-label">Your Rank</span>
                <span className="rank-value">{getRankBadge(userRank)}</span>
                <span className="rank-points">{user.loyalty_points || 0} pts</span>
              </div>
            )}
          </div>

          {isLoading ? (
            <div className="leaderboard-loading">
              <p>Loading rankings...</p>
            </div>
          ) : leaderboard.length === 0 ? (
            <div className="leaderboard-empty">
              <p>No rankings available yet.</p>
            </div>
          ) : (
            <div className="leaderboard-grid" ref={gridRef}>
              {leaderboard.map((entry, idx) => {
                const isCurrentUser = user && entry.username === user.username;
                return (
                  <div
                    key={entry.username || idx}
                    className={`leaderboard-card ${isCurrentUser ? 'is-current-user' : ''}`}
                  >
                    <div className="leaderboard-card-header">
                      <span className="leaderboard-rank">{getRankBadge(entry.rank || idx + 1)}</span>
                      <span className={`leaderboard-username ${isCurrentUser ? 'highlight' : ''}`}>
                        {entry.username}
                      </span>
                    </div>
                    <div className="leaderboard-card-body">
                      <div className="leaderboard-points">
                        <span className="points-value">{entry.loyalty_points}</span>
                        <span className="points-label">points</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default LeaderboardPage;

