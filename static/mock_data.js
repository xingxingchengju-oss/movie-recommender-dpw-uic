const MOCK_MOVIES = [
  {
    id: 1,
    title: "Inception",
    release_year: 2010,
    primary_genre: "Science Fiction",
    genres: ["Science Fiction", "Action", "Thriller"],
    overview: "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
    vote_average: 8.4,
    director: "Christopher Nolan",
    keywords: ["dream", "subconscious", "heist"]
  },
  {
    id: 2,
    title: "The Dark Knight",
    release_year: 2008,
    primary_genre: "Action",
    genres: ["Action", "Crime", "Drama"],
    overview: "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
    vote_average: 9.0,
    director: "Christopher Nolan",
    keywords: ["joker", "gotham", "vigilante"]
  },
  {
    id: 3,
    title: "Spirited Away",
    release_year: 2001,
    primary_genre: "Animation",
    genres: ["Animation", "Fantasy", "Adventure"],
    overview: "During her family's move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods, witches, and spirits, where humans are changed into beasts.",
    vote_average: 8.5,
    director: "Hayao Miyazaki",
    keywords: ["spirit", "bathhouse", "transformation"]
  },
  {
    id: 4,
    title: "Parasite",
    release_year: 2019,
    primary_genre: "Thriller",
    genres: ["Thriller", "Comedy", "Drama"],
    overview: "Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.",
    vote_average: 8.6,
    director: "Bong Joon-ho",
    keywords: ["class struggle", "dark comedy", "twist"]
  },
  {
    id: 5,
    title: "Interstellar",
    release_year: 2014,
    primary_genre: "Science Fiction",
    genres: ["Science Fiction", "Drama", "Adventure"],
    overview: "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival as Earth becomes uninhabitable.",
    vote_average: 8.6,
    director: "Christopher Nolan",
    keywords: ["space", "wormhole", "time dilation"]
  },
  {
    id: 6,
    title: "The Shawshank Redemption",
    release_year: 1994,
    primary_genre: "Drama",
    genres: ["Drama", "Crime"],
    overview: "Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.",
    vote_average: 9.3,
    director: "Frank Darabont",
    keywords: ["prison", "hope", "friendship"]
  },
  {
    id: 7,
    title: "Pulp Fiction",
    release_year: 1994,
    primary_genre: "Crime",
    genres: ["Crime", "Thriller", "Comedy"],
    overview: "The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.",
    vote_average: 8.9,
    director: "Quentin Tarantino",
    keywords: ["nonlinear", "hitman", "gangster"]
  },
  {
    id: 8,
    title: "Frozen",
    release_year: 2013,
    primary_genre: "Animation",
    genres: ["Animation", "Adventure", "Comedy"],
    overview: "When the newly crowned Queen Elsa accidentally uses her power to turn things into ice to curse her home in infinite winter, her sister Anna teams up with a mountain man to change the weather condition.",
    vote_average: 7.3,
    director: "Chris Buck",
    keywords: ["ice", "princess", "musical"]
  },
  {
    id: 9,
    title: "The Godfather",
    release_year: 1972,
    primary_genre: "Crime",
    genres: ["Crime", "Drama"],
    overview: "The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant youngest son.",
    vote_average: 9.2,
    director: "Francis Ford Coppola",
    keywords: ["mafia", "family", "power"]
  },
  {
    id: 10,
    title: "Your Name",
    release_year: 2016,
    primary_genre: "Animation",
    genres: ["Animation", "Drama", "Fantasy"],
    overview: "Two strangers find themselves linked in a bizarre way. When a connection forms, will distance be the only thing to keep them apart?",
    vote_average: 8.5,
    director: "Makoto Shinkai",
    keywords: ["body swap", "comet", "romance"]
  },
  {
    id: 11,
    title: "Mad Max: Fury Road",
    release_year: 2015,
    primary_genre: "Action",
    genres: ["Action", "Adventure", "Science Fiction"],
    overview: "An apocalyptic story set in the furthest reaches of our planet, in a stark desert landscape where humanity is broken.",
    vote_average: 7.6,
    director: "George Miller",
    keywords: ["post-apocalyptic", "chase", "desert"]
  },
  {
    id: 12,
    title: "The Grand Budapest Hotel",
    release_year: 2014,
    primary_genre: "Comedy",
    genres: ["Comedy", "Drama", "Crime"],
    overview: "The adventures of Gustave H, a legendary concierge at a famous European hotel between the wars, and Zero Moustafa, the lobby boy who becomes his most trusted friend.",
    vote_average: 8.1,
    director: "Wes Anderson",
    keywords: ["hotel", "concierge", "adventure"]
  },
  {
    id: 13,
    title: "Gladiator",
    release_year: 2000,
    primary_genre: "Action",
    genres: ["Action", "Drama", "History"],
    overview: "A former Roman General sets out to exact vengeance against the corrupt emperor who murdered his family and sent him into slavery.",
    vote_average: 8.5,
    director: "Ridley Scott",
    keywords: ["rome", "gladiator", "revenge"]
  },
  {
    id: 14,
    title: "Whiplash",
    release_year: 2014,
    primary_genre: "Drama",
    genres: ["Drama", "Mystery"],
    overview: "A promising young drummer enrolls at a cut-throat music conservatory where his dreams of greatness are mentored by an instructor who will stop at nothing to realize a student's potential.",
    vote_average: 8.5,
    director: "Damien Chazelle",
    keywords: ["jazz", "drummer", "obsession"]
  },
  {
    id: 15,
    title: "Coco",
    release_year: 2017,
    primary_genre: "Animation",
    genres: ["Animation", "Fantasy", "Comedy"],
    overview: "Aspiring musician Miguel, confronted with his family's ancestral ban on music, enters the Land of the Dead to find his great-great-grandfather, a legendary singer.",
    vote_average: 8.2,
    director: "Lee Unkrich",
    keywords: ["day of the dead", "music", "family"]
  },
  {
    id: 16,
    title: "The Silence of the Lambs",
    release_year: 1991,
    primary_genre: "Thriller",
    genres: ["Thriller", "Crime", "Drama"],
    overview: "A young F.B.I. cadet must receive the help of an incarcerated and manipulative cannibal killer to help catch another serial killer.",
    vote_average: 8.6,
    director: "Jonathan Demme",
    keywords: ["serial killer", "fbi", "psychological"]
  }
];

const ALL_GENRES = [
  "All", "Action", "Adventure", "Animation", "Comedy", "Crime",
  "Drama", "Fantasy", "History", "Mystery", "Science Fiction", "Thriller"
];

const CHART_DATA = {
  productionByYear: {
    years: [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017],
    counts: [820,854,891,930,978,1043,1102,1189,1254,1318,1401,1476,1553,1620,1714,1832,1945,1203]
  },
  genreDistribution: {
    labels: ["Drama","Comedy","Thriller","Action","Romance","Horror","Science Fiction","Adventure","Crime","Animation","Fantasy","History"],
    values: [4820,3210,2540,2380,1960,1740,1520,1380,1250,980,760,540]
  },
  topDirectors: {
    names: ["Christopher Nolan","Hayao Miyazaki","Bong Joon-ho","Denis Villeneuve","Alfonso Cuarón","Wes Anderson","David Fincher","Quentin Tarantino","Martin Scorsese","Steven Spielberg"],
    ratings: [8.4,8.3,8.1,8.0,7.9,7.8,7.7,7.7,7.6,7.5],
    counts: [8,11,12,9,10,10,9,10,14,18]
  },
  ratingTrends: {
    years: [2000,2002,2004,2006,2008,2010,2012,2014,2016,2017],
    genres: {
      "Drama":        [7.1,7.0,7.2,7.1,7.3,7.2,7.4,7.3,7.2,7.1],
      "Action":       [6.4,6.3,6.5,6.4,6.6,6.5,6.7,6.6,6.5,6.4],
      "Science Fiction": [6.8,6.9,7.0,6.9,7.1,7.2,7.3,7.4,7.3,7.2],
      "Animation":    [7.2,7.3,7.4,7.5,7.6,7.5,7.7,7.6,7.8,7.7],
      "Thriller":     [6.9,6.8,7.0,6.9,7.1,7.0,7.2,7.1,7.0,6.9]
    }
  }
};