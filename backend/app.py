from flask import Flask, request, jsonify
from flask_cors import CORS
from models import init_db, SessionLocal, User, BetHistory
from provably_fair import generate_server_seed
from game_logic import spin_grid, evaluate_grid, compute_payout
import os

app = Flask(__name__)
CORS(app)
init_db()

# Cria usuário padrão em primeiro run
with SessionLocal() as db:
    user = db.query(User).filter_by(username='player1').first()
    if not user:
        server_seed, server_seed_hash = generate_server_seed()
        user = User(username='player1', balance=1000.0, server_seed=server_seed,
                    server_seed_hash=server_seed_hash, client_seed='client-seed', nonce=0)
        db.add(user)
        db.commit()

@app.get('/api/balance')
def get_balance():
    username = request.args.get('username', 'player1')
    with SessionLocal() as db:
        u = db.query(User).filter_by(username=username).first()
        if not u:
            return jsonify({'error':'user not found'}), 404
        return jsonify({'username': u.username, 'balance': round(u.balance,2),
                        'server_seed_hash': u.server_seed_hash, 'client_seed': u.client_seed, 'nonce': u.nonce})

@app.post('/api/bet')
def bet():
    data = request.get_json(force=True)
    amount = float(data.get('amount', 1))
    lines = int(data.get('lines', 10))
    username = data.get('username', 'player1')

    if amount <= 0 or lines <= 0 or lines > 10:
        return jsonify({'error':'invalid bet'}), 400

    with SessionLocal() as db:
        u = db.query(User).filter_by(username=username).first()
        if not u:
            return jsonify({'error':'user not found'}), 404
        bet_total = amount * lines
        if bet_total > u.balance:
            return jsonify({'error':'insufficient balance'}), 400

        # gera grade determinística via provably fair
        grid = spin_grid(u.server_seed, u.client_seed, u.nonce)
        result = evaluate_grid(grid, amount)
        payout = compute_payout(result.total_multiplier, lines, amount)
        net = payout - bet_total

        # atualiza saldo e nonce
        u.balance += net
        u.nonce += 1
        db.add(BetHistory(user_id=u.id, amount=bet_total, payout=payout, result_grid=str(grid)))
        db.commit()

        return jsonify({
            'grid': grid,
            'line_wins': result.line_wins,
            'total_multiplier': result.total_multiplier,
            'bet_total': bet_total,
            'payout': payout,
            'net': net,
            'balance': round(u.balance,2),
            'provably_fair': {
                'server_seed_hash': u.server_seed_hash,
                'client_seed': u.client_seed,
                'nonce': u.nonce - 1
            }
        })

@app.post('/api/payout')
def manual_payout():
    data = request.get_json(force=True)
    username = data.get('username', 'player1')
    amount = float(data.get('amount', 0))
    if amount <= 0:
        return jsonify({'error':'invalid amount'}), 400
    with SessionLocal() as db:
        u = db.query(User).filter_by(username=username).first()
        if not u:
            return jsonify({'error':'user not found'}), 404
        if amount > u.balance:
            return jsonify({'error':'insufficient balance'}), 400
        u.balance -= amount
        db.commit()
        return jsonify({'message':'payout processed', 'balance': round(u.balance,2)})

@app.post('/api/rotate-seed')
def rotate_seed():
    # opcional: reseta server_seed (revela o antigo para verificação)
    data = request.get_json(force=True)
    username = data.get('username', 'player1')
    with SessionLocal() as db:
        u = db.query(User).filter_by(username=username).first()
        if not u:
            return jsonify({'error':'user not found'}), 404
        old_seed = u.server_seed
        old_hash = u.server_seed_hash
        from provably_fair import generate_server_seed
        new_seed, new_hash = generate_server_seed()
        u.server_seed = new_seed
        u.server_seed_hash = new_hash
        u.nonce = 0
        db.commit()
        
        return jsonify({'old_server_seed': old_seed, 'old_server_seed_h