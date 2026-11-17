# MOTOSPHERE
## Complete Project Design & Development Specification

**Project:** MotoSphere  
**Type:** Global motorsport information, intelligence and mapping platform  
**Primary interface:** Interactive 3D Earth  
**Initial development:** Windows 11 PC  
**Long-term objective:** A comprehensive worldwide motocross racing database and discovery platform.

---

# 1. PROJECT VISION

Build a comprehensive global motocross information platform that automatically discovers, collects, organises and presents freely accessible information about motocross and related off-road motorcycle racing worldwide.

The application should become a central place to explore:

- Where motocross tracks are located.
- What races and events are happening around the world.
- Upcoming race calendars and championship rounds.
- Historical race results and individual moto classifications.
- Championship standings, points and previous champions.
- Riders, teams, manufacturers and racing statistics.
- Amateur, youth, veteran and professional racing.
- Motocross news and announcements.

The defining feature is a fully interactive, Google Earth-style 3D globe.

The globe must be the centrepiece of the application, not a small map inside a conventional dashboard.

Users should be able to explore the entire world, zoom into individual countries, discover tracks, inspect circuits and open detailed information panels directly from map markers.

The application should continuously grow its database through automated daily information gathering.

# 2. RACING COVERAGE

## 2.1 Primary disciplines

The system must support:

1. Outdoor Motocross (MX).
2. Supercross (SX).
3. Amateur Motocross.
4. Youth and junior motocross.
5. Veteran and masters racing.
6. Enduro.
7. Hard Enduro.

The data model must support additional disciplines without requiring a database redesign.

## 2.2 Geographic coverage

Worldwide coverage is the ultimate objective.

Development and data acquisition should initially prioritise:

- United Kingdom.
- Europe.
- United States.
- Canada.
- Other major international motocross markets.

Expansion must continue into other countries and regions.

Do not restrict the system to countries with major professional championships.

Local clubs, regional championships, amateur meetings and independent circuits are equally important parts of the overall directory.

# 3. THE GLOBAL 3D EARTH

This is the most important interface component.

Use CesiumJS or another technically superior solution if a clear advantage can be demonstrated.

## 3.1 Globe behaviour

The globe must provide:

- Full 360-degree rotation.
- Free horizontal movement.
- Vertical panning.
- Smooth zooming in and out.
- Mouse-wheel zoom.
- Click-and-drag navigation.
- Tilt and perspective controls.
- Keyboard navigation where practical.
- Smooth camera transitions.
- Full-screen exploration.
- Responsive performance at different zoom levels.

The user must be able to zoom continuously from an entire-Earth view down to individual motocross circuits.

It should feel like exploring Google Earth.

## 3.2 Imagery and terrain

Provide:

- Satellite imagery as the preferred default.
- Realistic terrain where available.
- Country and regional boundaries.
- Geographic labels.
- Terrain-aware positioning of markers.
- Appropriate attribution for all imagery providers.

Do not use Google Earth imagery or Google Maps assets without the appropriate licence.

Investigate genuinely free imagery and terrain providers first.

Allow alternative imagery providers to be configured without rewriting the globe.

If a provider requires an API key, subscription or access token, explain this clearly and provide a configurable integration.

Never claim imagery is free unless its actual usage terms have been verified.

## 3.3 Map markers

The globe must display different marker categories:

- Motocross tracks.
- Supercross venues.
- Enduro venues.
- Upcoming races.
- Live/current race events.
- Historical event locations.
- Championship locations.

Different categories should have recognisable visual identities.

Markers must avoid overwhelming the globe.

Implement clustering at wider geographic views. As users zoom closer, individual markers should become visible.

Filters must allow marker categories to be switched on and off.

## 3.4 Track exploration

When a user zooms into a circuit, display all available information about that location.

Where available, include:

- Track name.
- Country and region.
- Coordinates.
- Circuit photographs.
- Website.
- Contact details.
- Track type.
- Surface information.
- Facilities.
- Associated clubs.
- Associated championships.
- Upcoming events.
- Historical race events.
- Results recorded at the venue.

Show the actual track outline or circuit layout if a reliable public source exists.

Never fabricate a circuit layout.

# 4. MAP INFORMATION PANELS

Clicking a marker must open a detailed, expandable information panel.

The panel should be context-sensitive.

## 4.1 Track panel

Display:

- Track identity.
- Location and coordinates.
- Track details.
- Associated organisation.
- Website and contact information.
- Upcoming events.
- Previous events.
- Available results.
- Championships associated with the venue.
- Related photographs and source links.

## 4.2 Event panel

Display:

- Event name.
- Date and time.
- Venue.
- Country.
- Racing discipline.
- Championship.
- Classes.
- Promoter or organiser.
- Event website.
- Entry information where publicly available.
- Results when published.
- Status: upcoming, underway, completed, cancelled or postponed.

## 4.3 Championship panel

Display:

- Championship name.
- Organiser.
- Country or international coverage.
- Current season.
- Calendar.
- Round locations.
- Classes.
- Championship standings.
- Previous champions.
- Historical seasons where available.

## 4.4 Rider panel

Display:

- Rider name.
- Nationality where publicly documented.
- Racing number.
- Current team.
- Manufacturer.
- Classes.
- Current championships.
- Race history.
- Results.
- Wins and podiums.
- Championship statistics.

Keep rider identities properly linked so that the same person is not accidentally duplicated because of spelling variations.

## 4.5 Expandable design

Panels should be easy to navigate without hiding the globe completely.

Use expandable sections, tabs or nested information areas.

Provide links to original information sources.

# 5. GLOBAL RACING DATABASE

The application must build and maintain a structured database rather than simply displaying scraped text.

## 5.1 Core entities

Create properly related database tables for:

- Countries.
- Regions.
- Tracks.
- Organisations.
- Promoters.
- Events.
- Championships.
- Championship seasons.
- Championship rounds.
- Racing classes.
- Riders.
- Teams.
- Manufacturers.
- Bikes.
- Individual races.
- Individual motos.
- Race entries.
- Race results.
- Championship standings.
- News articles.
- Media references.
- Information sources.
- Data collection runs.

## 5.2 Race results

Where information is available, collect:

- Event.
- Round.
- Date.
- Championship.
- Class.
- Race or moto number.
- Rider.
- Team.
- Manufacturer.
- Finishing position.
- Race time.
- Laps completed.
- Points awarded.
- DNF, DNS and DSQ status.

Keep individual moto results separate from overall event results.

Never assume an overall result is equivalent to an individual moto classification.

## 5.3 Championship standings

Store:

- Championship.
- Season.
- Class.
- Rider or team.
- Position.
- Total points.
- Wins.
- Podiums.
- Round-by-round points where available.

Preserve historical standings rather than overwriting previous seasons.

Only calculate standings when the scoring rules and source data are sufficiently complete.

Otherwise display the official published standings.

# 6. HISTORICAL DATA

The initial operational focus is the current racing season.

However, the database architecture must support historical information extending as far back as reliable freely accessible records can be discovered.

Collect historical information opportunistically during development and subsequent scanning.

Historical data sources may include:

- Official championship archives.
- Governing body records.
- Results databases.
- Archived championship calendars.
- Historical publications.
- Publicly accessible documents and PDFs.
- Club and promoter archives.

Historical records must retain their original dates and source references.

Do not present estimated or reconstructed information as verified official results.

Clearly distinguish between:

- Officially published records.
- Independently published records.
- Reconstructed historical records.
- Unverified historical references.

# 7. AUTOMATED INFORMATION COLLECTION

This is the engine that makes the project useful.

Build a modular collection system capable of finding and updating information from publicly accessible sources worldwide.

## 7.1 Source categories

Investigate and collect from:

1. Official governing bodies.
2. Official championship websites.
3. Championship organisers.
4. Race promoters.
5. Individual motocross tracks.
6. Local motorcycle clubs.
7. Regional racing organisations.
8. Public results databases.
9. Motocross news publications.
10. Publicly accessible community websites.
11. Public social media pages where permitted.
12. Publicly accessible historical archives.

## 7.2 Collection methods

Use the most appropriate method for each source:

- Official APIs.
- Public structured feeds.
- RSS feeds.
- Public datasets.
- Permitted HTML extraction.
- Structured public documents.
- Public JSON endpoints where authorised.
- Sitemap discovery.
- Search-engine discovery where permitted.
- Human-submitted source references.

Do not build one enormous scraper.

Create independent source adapters so that individual sources can be developed, tested, disabled and maintained separately.

## 7.3 Source registry

Maintain a source registry containing:

- Source name.
- Website.
- Country.
- Source category.
- Available information types.
- Collection method.
- Last successful scan.
- Last attempted scan.
- Scan frequency.
- Reliability score.
- Current health.
- Error information.
- Usage restrictions.
- Terms and licence information.

The system must know where every piece of information originated.

## 7.4 Daily automated scanning

Implement an automated daily scanning schedule.

The collection engine should:

1. Identify sources due for scanning.
2. Check source availability.
3. Collect new information.
4. Detect changes to existing information.
5. Validate collected data.
6. Identify possible duplicates.
7. Update database records.
8. Record collection history.
9. Report failures.
10. Queue uncertain records for review.

Do not repeatedly download unchanged information unnecessarily.

Use conditional requests, caching and incremental updates where supported.

## 7.5 Discovery of new sources

The application should be capable of discovering potential new information sources.

Discovered sources must enter a review or validation process before becoming active collectors.

Do not allow uncontrolled recursive crawling.

Use a configurable crawl scope, source limits and domain restrictions.

# 8. DATA QUALITY AND INTEGRITY

Accuracy is more important than database size.

Every imported record should retain:

- Original source URL.
- Source identity.
- Collection timestamp.
- Original publication date where known.
- Last verification timestamp.
- Extraction method.
- Confidence level.
- Verification status.

Implement duplicate detection for:

- Tracks.
- Riders.
- Teams.
- Events.
- Championships.
- Race results.

Use geographic proximity, aliases, dates and related entities to assist matching.

Do not automatically merge uncertain identities.

Create a review queue for conflicting or ambiguous records.

Never invent missing values.

Use explicit unknown/null values instead.

Keep original source material or permitted evidence references so that records can be checked later.

# 9. SEARCH AND FILTERING

Provide global search across the database.

Users should be able to search for:

- Tracks.
- Events.
- Riders.
- Teams.
- Championships.
- Countries.
- Regions.
- Results.
- Manufacturers.

Provide filters for:

- Country.
- Date range.
- Racing discipline.
- Championship.
- Class.
- Event status.
- Rider.
- Team.
- Track.

Filters must interact with the globe so that the map updates to show matching results.

# 10. STATISTICS AND COMPARISON

Provide comparison tools for riders, teams and championships.

## 10.1 Rider comparisons

Compare available statistics such as:

- Race wins.
- Podiums.
- Championship points.
- Finishing positions.
- Average finishing position.
- Season performance.
- Head-to-head results.
- Career results.

## 10.2 Team comparisons

Compare:

- Riders.
- Wins.
- Podiums.
- Championship points.
- Season performance.

## 10.3 Championship comparisons

Compare:

- Seasons.
- Classes.
- Number of rounds.
- Riders.
- Participating countries.
- Historical winners.

Only display statistics that can be supported by collected data.

Explain when comparisons are incomplete.

# 11. NEWS AND ANNOUNCEMENTS

Provide a central motocross news feed.

Collect permitted publicly accessible motocross news from recognised publications, championship organisers and clubs.

Display:

- Headline.
- Publisher.
- Publication date.
- Short summary.
- Relevant country.
- Relevant championship or event.
- Original article link.

Do not republish complete copyrighted articles.

Do not copy photographs without permission.

# 12. APPLICATION INTERFACE

The application should feel like a dedicated global motorsport intelligence platform.

It must not look like a generic admin dashboard.

## 12.1 Main layout

The globe should occupy the majority of the screen.

Suggested interface:

**Top bar**
- Application logo/name.
- Global search.
- Current date.
- Data update status.
- Settings.

**Left panel**
- Explore.
- Events.
- Tracks.
- Championships.
- Riders.
- Teams.
- Results.
- News.
- Statistics.

**Centre**
- Full interactive 3D Earth.
- Geographic markers.
- Camera controls.
- Map filters.

**Right panel**
- Selected track/event/rider details.
- Expandable information.
- Related events and results.

Panels should be collapsible to maximise globe viewing space.

## 12.2 Visual design

Aim for a professional motorsport intelligence interface.

Requirements:

- Dark visual theme.
- Clear typography.
- High-contrast information.
- Restrained accent colours.
- Recognisable racing icons.
- Smooth transitions.
- Professional charts and tables.
- Clear loading states.
- Useful error messages.
- No unnecessary visual clutter.

Prioritise usability over decorative effects.

# 13. TECHNICAL ARCHITECTURE

Claude should evaluate the following proposed stack and make justified changes if necessary.

### Front end
- React.
- TypeScript.
- Modern component architecture.
- CesiumJS for the globe.
- Responsive interface.

### Backend
- Python.
- FastAPI.
- Modular service architecture.
- Separate data collection workers.

### Database
- PostgreSQL.
- PostGIS for geographic queries.
- Proper indexing and relational integrity.

### Background processing
- Scheduled daily collection.
- Independent source adapters.
- Retry handling.
- Job history.
- Failure monitoring.

A lightweight job scheduler is acceptable initially. Introduce Redis, Celery or another queue only when the workload justifies it.

### Development environment
- Windows 11 compatibility.
- Local development first.
- Simple startup and shutdown.
- Environment-based configuration.
- No unnecessary Docker requirement.

### Deployment
Design the system so it can eventually be hosted online without a complete rewrite.

Claude must investigate hosting costs, storage requirements, database hosting, imagery licensing and background processing before recommending a production deployment.

Do not assume that a globally comprehensive service can run indefinitely for free.

# 14. SOURCE AND LICENSING COMPLIANCE

The project must only collect information through lawful and permitted methods.

Mandatory rules:

- Respect robots.txt as a collection policy signal.
- Respect website terms of service.
- Respect API usage limits.
- Identify the application in automated requests.
- Implement per-domain rate limits.
- Cache downloaded information.
- Avoid unnecessary repeated requests.
- Respect copyright and database rights.
- Respect privacy and data protection requirements.
- Do not bypass logins, paywalls, CAPTCHAs or anti-bot protections.
- Do not circumvent access restrictions.
- Do not scrape private social media content.
- Do not copy protected photographs or full articles.
- Keep licence and attribution information.

A website being publicly visible does not automatically mean its entire contents can be copied or redistributed.

When collection is not permitted, store a reference to the original source rather than copying the content.

# 15. ADMINISTRATION AND MONITORING

Create an administration area.

Include:

- Database statistics.
- Total tracks.
- Total events.
- Total championships.
- Total riders.
- Total results.
- Total sources.
- Daily collection activity.
- Failed collection jobs.
- Source health.
- Duplicate records.
- Unverified information.
- Records awaiting review.

Allow the administrator to:

- Enable or disable individual sources.
- Trigger a manual scan.
- Retry failed jobs.
- Review uncertain records.
- Correct inaccurate information.
- Merge confirmed duplicate entities.
- Inspect collection logs.
- Configure scan schedules.

# 16. DEVELOPMENT PHASES

Every phase must be divided into small, independently testable tasks.

Do not implement an entire phase as one task.

## Phase 1 – Foundation
- Inspect the development environment.
- Establish architecture.
- Create project structure.
- Configure database.
- Build basic application shell.
- Establish testing infrastructure.

## Phase 2 – Interactive Earth
- Integrate CesiumJS.
- Establish imagery and terrain.
- Implement camera controls.
- Implement zoom and navigation.
- Build marker system.
- Build marker clustering.
- Build expandable information panels.
- Test worldwide navigation.

## Phase 3 – Track Directory
- Build geographic database.
- Discover track information sources.
- Import initial worldwide track records.
- Implement track search.
- Display track pins.
- Build track information panels.
- Validate geographic accuracy.

## Phase 4 – Event Collection
- Build event database.
- Implement event source adapters.
- Collect upcoming race calendars.
- Collect event information.
- Implement event status.
- Connect events to tracks and championships.

## Phase 5 – Championships
- Championship database.
- Seasons and rounds.
- Classes.
- Standings.
- Points.
- Historical championship information.

## Phase 6 – Results
- Race and moto records.
- Rider identity matching.
- Individual results.
- Overall results.
- Historical archives.
- Data validation.

## Phase 7 – Riders and Teams
- Rider profiles.
- Team profiles.
- Manufacturer information.
- Career records.
- Statistics.

## Phase 8 – Automated Collection
- Daily scheduler.
- Source registry.
- Incremental scanning.
- Duplicate detection.
- Failure handling.
- Source discovery.
- Monitoring.

## Phase 9 – Search and Comparison
- Global search.
- Advanced filters.
- Rider comparisons.
- Team comparisons.
- Championship comparisons.
- Statistics.

## Phase 10 – News and Expansion
- News feed.
- More international sources.
- Historical data expansion.
- Additional disciplines.
- Performance improvements.
- Deployment preparation.

These phases are an implementation guide, not permission to skip testing or introduce unfinished dependencies.

# 17. SUCCESS CRITERIA

The finished application should:

1. Present a fully navigable 3D Earth.
2. Allow continuous zoom from global to circuit-level views.
3. Display geographically accurate motocross locations.
4. Display upcoming races.
5. Connect events to their tracks and championships.
6. Maintain historical event information.
7. Display race results and individual moto results where available.
8. Display championship standings.
9. Maintain rider and team profiles.
10. Automatically collect information daily.
11. Record the provenance of all collected information.
12. Detect duplicates and conflicting records.
13. Provide useful search and filtering.
14. Provide meaningful statistics and comparisons.
15. Remain stable when individual sources fail.
16. Work locally on Windows.
17. Support future hosted deployment.

# 18. FINAL DEVELOPMENT PRINCIPLE

Build a reliable global motocross information platform, not a demonstration scraper.

The application must be designed to expand continuously as new sources, countries, tracks, championships and historical records become available.

The database should become more valuable with every successful collection cycle.

The 3D Earth must remain the defining feature of the experience.

Accuracy, usability, extensibility and reliability take priority over artificially inflating the number of records.

**The ultimate ambition: Explore the entire world and discover everything happening in motocross, past and present.**