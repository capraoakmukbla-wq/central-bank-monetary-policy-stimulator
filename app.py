import os
import sqlite3
import random
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB_FILE = 'game.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS economic_history")
        cursor.execute("""
            CREATE TABLE economic_history (
                quarter INTEGER PRIMARY KEY, interest_rate REAL, inflation REAL, output_gap REAL, score INTEGER
            )
        """)
        cursor.execute("INSERT INTO economic_history VALUES (0, 4.0, 2.0, 0.0, 100)")
        conn.commit()

@app.route('/')
def index():
    if not os.path.exists(DB_FILE):
        init_db()
        
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get latest stats
        state = cursor.execute("SELECT * FROM economic_history ORDER BY quarter DESC LIMIT 1").fetchone()
        # Get all history rows
        history = cursor.execute("SELECT * FROM economic_history ORDER BY quarter ASC").fetchall()

    # Pack data neatly for the chart
    chart_data = {
        "quarters": [r['quarter'] for r in history],
        "rates": [r['interest_rate'] for r in history],
        "inflation": [r['inflation'] for r in history],
        "gap": [r['output_gap'] for r in history]
    }

    # Win/Loss conditions
    game_over = False
    message = "Economy stable. Make your adjustments, Governor."
    
    if state['quarter'] >= 12:
        game_over = True
        message = f"Victory! You completed your term. Final Score: {state['score']}/100!"
    elif state['inflation'] >= 6.0 or state['inflation'] <= -1.0:
        game_over = True
        message = "Game Over! Inflation spiraled out of control!"
    elif state['output_gap'] <= -5.0:
        game_over = True
        message = "Game Over! The economy fell into a deep economic crash!"

    return render_template('index.html', state=state, chart_data=chart_data, game_over=game_over, message=message)

@app.route('/next_quarter', methods=['POST'])
def next_quarter():
    new_rate = float(request.form.get('interest_rate', 4.0))
    
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        last = cursor.execute("SELECT * FROM economic_history ORDER BY quarter DESC LIMIT 1").fetchone()
        
        # Simple Math Engine: Raising rates lowers inflation/growth, lowering rates raises them
        rate_change = new_rate - last['interest_rate']
        random_shock = random.choice([-0.5, 0.0, 0.5]) # Adds unexpected real-world surprises
        
        new_gap = round(last['output_gap'] - (0.5 * rate_change) + random_shock, 2)
        new_inf = round(last['inflation'] + (0.3 * new_gap), 2)
        
        # Calculate penalty score based on how far away inflation is from 2%
        penalty = abs(new_inf - 2.0) * 10
        new_score = max(0, int(last['score'] - penalty))
        
        cursor.execute("INSERT INTO economic_history VALUES (?, ?, ?, ?, ?)", 
                       (last['quarter'] + 1, new_rate, new_inf, new_gap, new_score))
        conn.commit()
        
    return redirect(url_for('index'))

@app.route('/reset')
def reset():
    init_db()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
