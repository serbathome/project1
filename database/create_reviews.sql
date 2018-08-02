create table reviews (
    id serial primary key,
    bookid integer references books(id),
    userid integer references users(id),
    rating integer check(rating >= 0 and rating <= 5),
    comments text
)
