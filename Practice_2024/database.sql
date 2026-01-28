CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE vacancies (
    vacancy_id INTEGER PRIMARY KEY,
    title VARCHAR(255),
    company VARCHAR(255),
    salary INTEGER,
    experience VARCHAR(255),
    city VARCHAR(255),
    description TEXT,
    schedule VARCHAR(255)
);
