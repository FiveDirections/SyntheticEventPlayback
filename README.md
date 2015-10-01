# SyntheticEventPlayback

This project is designed to generate "realistic" synthetic Windows Event data.
Our approach has been to record the events generated by a discrete user action 
such as opening an email, or browsing to a web page. These events are then
edited to remove any potential personally identifiable information (PII) to
create a template.

## Recording Engine
We'll be releasing this code in the near future.

## Playback Engine
The playback engine randomly selects a template and fills in any PII variables
and sends the event over HTTP to a designated host/port pair. A number of hosts
can be simulated from a single command line.

### Usage: XXXX TO DO XXXX

### Dependencies
The playback engine requires the Twisted package https://twistedmatrix.com/trac/ and
OpenSSL (if you want to use https).

## Templates
We currently have forty six templates, and we (along with the community) hope to add
more templates in the future.

To see the full list of templates, look in the templates directory.

## License
This software is released under the Apache License (V2). See the LICENSE.md for
more information.