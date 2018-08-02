create table users
(
    id serial primary key,
    name text not null,
    password text not null
);

create extension pgcrypto;

insert into users
(
    name,password
)
    values
(
    'serbathome',
    crypt('mypassword', gen_salt('bf'))
);

select id from users
where name = 'serbathome' and
password = crypt('mypassword', password);
