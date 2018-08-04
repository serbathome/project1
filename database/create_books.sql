create table books (
    id serial primary key,
    isbn varchar(32),
    title varchar(128),
    author varchar(128),
    year integer
)
