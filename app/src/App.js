import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HomePage from "./components/home";
import SelectSupermarketPage from "./components/selection";
import ShoppingListPage from "./components/shopping-list";
import ResultsPage from "./components/ResultsPage";
import ContactPage from "./components/support";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/select-supermarket" element={<SelectSupermarketPage />} />
        <Route path="/shopping-list" element={<ShoppingListPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/contact" element={<ContactPage />} />
      </Routes>
    </Router>
  );
}

export default App;
