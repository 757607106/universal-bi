ALTER TABLE datasources ADD COLUMN owner_id INTEGER REFERENCES users(id);
ALTER TABLE datasets ADD COLUMN owner_id INTEGER REFERENCES users(id);
