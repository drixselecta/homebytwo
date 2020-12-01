// Import the main Sass file
import 'stylesheets/homebytwo.scss';

// UI
import 'ui/icons';

import '../../node_modules/leaflet/dist/leaflet.css';
import 'leaflet-tilelayer-swiss';

const HomeByTwo = {};

import L from 'leaflet';

HomeByTwo.L = L;

import LeafletMap from 'app/LeafletMap';

HomeByTwo.LeafletMap = LeafletMap;

Object.assign(window, {HomeByTwo});

import {Elm} from '../elm/src/Main.elm';

HomeByTwo.Elm = Elm;
