import { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Toaster, toast } from 'react-hot-toast';
import { FaSearch, FaChartLine, FaTrophy, FaExchangeAlt, FaSadTear } from 'react-icons/fa';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Header component with pixelated title
const Header = () => {
  return (
    <div className="header">
      <div className="title-container">
        <img 
          src="https://images.unsplash.com/photo-1639768939489-025b90ba9f23" 
          alt="Pain or Gains"
          className="title-image"
        />
        <h1 className="title">Pain or Gains</h1>
      </div>
      <p className="subtitle">Memecoin Trade Analysis</p>
    </div>
  );
};

// Search component
const Search = ({ onSearch }) => {
  const [wallet, setWallet] = useState("");
  const [blockchain, setBlockchain] = useState("solana");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!wallet) {
      toast.error("Please enter a wallet address");
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await axios.post(`${API}/analyze`, {
        wallet_address: wallet,
        blockchain: blockchain
      });
      
      onSearch(response.data);
      toast.success("Analysis complete!");
    } catch (error) {
      console.error("Error analyzing wallet:", error);
      toast.error("Failed to analyze wallet. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="search-container">
      <form onSubmit={handleSubmit}>
        <div className="tab-container">
          <button 
            type="button"
            className={`tab ${blockchain === "solana" ? "active" : ""}`}
            onClick={() => setBlockchain("solana")}
          >
            Solana
          </button>
          <button 
            type="button"
            className={`tab ${blockchain === "base" ? "active" : ""}`}
            onClick={() => setBlockchain("base")}
          >
            Base
          </button>
        </div>
        
        <div className="search-input-container">
          <input
            type="text"
            placeholder={`Enter ${blockchain} wallet address...`}
            value={wallet}
            onChange={(e) => setWallet(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="search-button" disabled={isLoading}>
            {isLoading ? "Analyzing..." : <FaSearch />}
          </button>
        </div>
      </form>
    </div>
  );
};

// Results component
const Results = ({ results }) => {
  if (!results) return null;
  
  return (
    <div className="results-container">
      <h2>Analysis Results for {results.wallet_address.slice(0, 6)}...{results.wallet_address.slice(-4)}</h2>
      
      <div className="stats-grid">
        <div className="stat-card best-trade">
          <div className="stat-icon"><FaTrophy /></div>
          <h3>Best Trade</h3>
          <p className="stat-value">${results.best_trade_profit.toFixed(2)}</p>
          <p className="stat-token">{results.best_trade_token}</p>
        </div>
        
        <div className="stat-card best-multiplier">
          <div className="stat-icon"><FaChartLine /></div>
          <h3>Best Multiplier</h3>
          <p className="stat-value">{results.best_multiplier.toFixed(2)}x</p>
          <p className="stat-token">{results.best_multiplier_token}</p>
        </div>
        
        <div className="stat-card pnl">
          <div className="stat-icon"><FaExchangeAlt /></div>
          <h3>All-time PnL</h3>
          <p className={`stat-value ${results.all_time_pnl >= 0 ? "positive" : "negative"}`}>
            ${results.all_time_pnl.toFixed(2)}
          </p>
          <p className="stat-token">Total</p>
        </div>
        
        <div className="stat-card worst-trade">
          <div className="stat-icon"><FaSadTear /></div>
          <h3>Worst Trade</h3>
          <p className="stat-value negative">${results.worst_trade_loss.toFixed(2)}</p>
          <p className="stat-token">{results.worst_trade_token}</p>
        </div>
      </div>
    </div>
  );
};

// Leaderboard component
const Leaderboard = () => {
  const [statType, setStatType] = useState("best_trade");
  const [blockchain, setBlockchain] = useState("solana");
  const [leaderboard, setLeaderboard] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  useEffect(() => {
    fetchLeaderboard();
  }, [statType, blockchain]);
  
  const fetchLeaderboard = async () => {
    setIsLoading(true);
    
    try {
      const response = await axios.get(`${API}/leaderboard/${statType}?blockchain=${blockchain}`);
      setLeaderboard(response.data);
    } catch (error) {
      console.error("Error fetching leaderboard:", error);
      toast.error("Failed to load leaderboard data");
    } finally {
      setIsLoading(false);
    }
  };
  
  const getStatTypeLabel = () => {
    switch (statType) {
      case "best_trade": return "Best Trade";
      case "best_multiplier": return "Best Multiplier";
      case "all_time_pnl": return "All-time PnL";
      case "worst_trade": return "Worst Trade";
      default: return "Unknown";
    }
  };
  
  const formatValue = (entry) => {
    switch (statType) {
      case "best_trade": return `$${entry.value.toFixed(2)}`;
      case "best_multiplier": return `${entry.value.toFixed(2)}x`;
      case "all_time_pnl": return `$${entry.value.toFixed(2)}`;
      case "worst_trade": return `$${entry.value.toFixed(2)}`;
      default: return entry.value;
    }
  };
  
  return (
    <div className="leaderboard-container">
      <h2>Leaderboard</h2>
      
      <div className="leaderboard-controls">
        <div className="blockchain-tabs">
          <button 
            className={`tab ${blockchain === "solana" ? "active" : ""}`}
            onClick={() => setBlockchain("solana")}
          >
            Solana
          </button>
          <button 
            className={`tab ${blockchain === "base" ? "active" : ""}`}
            onClick={() => setBlockchain("base")}
          >
            Base
          </button>
        </div>
        
        <div className="stat-tabs">
          <button 
            className={`tab ${statType === "best_trade" ? "active" : ""}`}
            onClick={() => setStatType("best_trade")}
          >
            Best Trade
          </button>
          <button 
            className={`tab ${statType === "best_multiplier" ? "active" : ""}`}
            onClick={() => setStatType("best_multiplier")}
          >
            Best Multiplier
          </button>
          <button 
            className={`tab ${statType === "all_time_pnl" ? "active" : ""}`}
            onClick={() => setStatType("all_time_pnl")}
          >
            All-time PnL
          </button>
          <button 
            className={`tab ${statType === "worst_trade" ? "active" : ""}`}
            onClick={() => setStatType("worst_trade")}
          >
            Worst Trade
          </button>
        </div>
      </div>
      
      {isLoading ? (
        <div className="loading">Loading leaderboard data...</div>
      ) : (
        <div className="leaderboard-table-container">
          <table className="leaderboard-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Wallet</th>
                <th>{getStatTypeLabel()}</th>
                <th>Token</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.length === 0 ? (
                <tr>
                  <td colSpan="4">No data available. Search for wallets to populate the leaderboard.</td>
                </tr>
              ) : (
                leaderboard.map((entry) => (
                  <tr key={entry.wallet_address}>
                    <td>#{entry.rank}</td>
                    <td>{entry.wallet_address.slice(0, 6)}...{entry.wallet_address.slice(-4)}</td>
                    <td className={statType === "worst_trade" ? "negative" : ""}>{formatValue(entry)}</td>
                    <td>{entry.token}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Main Home component
const Home = () => {
  const [results, setResults] = useState(null);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  
  const handleSearch = (data) => {
    setResults(data);
    setShowLeaderboard(false);
  };
  
  return (
    <div className="container">
      <Header />
      
      <div className="main-content">
        <Search onSearch={handleSearch} />
        
        <div className="view-toggle">
          <button 
            className={`toggle-button ${!showLeaderboard ? "active" : ""}`}
            onClick={() => setShowLeaderboard(false)}
          >
            Results
          </button>
          <button 
            className={`toggle-button ${showLeaderboard ? "active" : ""}`}
            onClick={() => setShowLeaderboard(true)}
          >
            Leaderboard
          </button>
        </div>
        
        {showLeaderboard ? (
          <Leaderboard />
        ) : (
          results ? <Results results={results} /> : (
            <div className="no-results">
              <p>Enter a wallet address to analyze memecoin trades</p>
            </div>
          )
        )}
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <Toaster position="top-right" />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;