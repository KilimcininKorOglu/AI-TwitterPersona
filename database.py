import sqlite3          # Built-in SQLite database interface
import datetime as dt   # For timestamp generation
import os              # For environment variable access
import threading       # For thread-safe database operations
from config import get_config  # Centralized configuration

# Database Configuration - customizable via environment variables
dbName = get_config("DB_NAME", "twitter.db")      # Database file name (default: twitter.db)
tableName = get_config("TABLE_NAME", "tweets")    # Table name for storing tweets (default: tweets)

# SECURITY: Whitelist of allowed table names to prevent SQL injection
ALLOWED_TABLE_NAMES = {'tweets', 'prompts', 'persona_settings', 'test_tweets'}

def validate_table_name(table_name):
    """
    Validate table name against whitelist to prevent SQL injection.

    Args:
        table_name (str): Table name to validate

    Returns:
        bool: True if table name is safe, False otherwise
    """
    if not table_name or not isinstance(table_name, str):
        return False

    # Check against whitelist
    if table_name not in ALLOWED_TABLE_NAMES:
        print(f"[ERROR] Invalid table name '{table_name}'. Allowed: {ALLOWED_TABLE_NAMES}")
        return False

    # Additional validation: alphanumeric + underscore only
    if not table_name.replace('_', '').isalnum():
        print(f"[ERROR] Table name contains invalid characters: {table_name}")
        return False

    return True

# Validate configured table name on module load
if not validate_table_name(tableName):
    print(f"[ERROR] Configured table name '{tableName}' is not allowed. Using default 'tweets'")
    tableName = "tweets"

# Thread safety for database operations
db_lock = threading.Lock()

def get_tweet_time():
    """
    Generate formatted timestamp components for tweet logging.

    Returns:
        tuple: (tweet_time, tweet_date, tweet_day) as strings
               - tweet_time: Time in ISO format HH:MM:SS
               - tweet_date: Date in ISO format YYYY-MM-DD
               - tweet_day: Full day name (e.g., Thursday)
    """
    now = dt.datetime.now()  # Get current datetime
    tweet_time = now.strftime("%H:%M:%S")       # ISO format: 14:30:45
    tweet_date = now.strftime("%Y-%m-%d")       # ISO format: 2025-08-30
    tweet_day = now.strftime("%A")              # Format: Thursday

    return tweet_time, tweet_date, tweet_day

def get_db_connection():
    """
    Establish connection to the SQLite database.

    Returns:
        sqlite3.Connection or None: Database connection object if successful,
                                   None if connection fails
    """
    try:
        # Connect to SQLite database with thread-safe settings
        conn = sqlite3.connect(dbName, check_same_thread=False)

        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL;')

        # Set timeout for concurrent access
        conn.execute('PRAGMA busy_timeout=30000;')  # 30 seconds

        print("[+] Database Connected (Thread-safe)")
        return conn
    except Exception as e:
        # Handle any database connection errors
        print(f"[-] Connection Failed. {e}")
        return None

def createDatabase():
    """
    Create the SQLite database and tweets table if they don't exist.

    Database Schema:
    - id: Auto-incrementing primary key
    - tweet_text: The actual tweet content (required)
    - tweet_type: Type of tweet (e.g., 'tweet', 'retweet')
    - sent: Boolean indicating if tweet was posted successfully
    - tweet_time: Time of tweet in HH:MM format
    - tweet_date: Date of tweet in DD-MM-YY format
    - tweet_day: Day of week when tweet was posted
    - created_at: Automatic timestamp of database entry creation
    """
    db = get_db_connection()
    if db is None:
        return  # Exit if database connection failed

    try:
        cursor = db.cursor()
        # SECURITY: Validate table name before using in SQL
        if not validate_table_name(tableName):
            print(f"[ERROR] Cannot create table with invalid name: {tableName}")
            return

        # SQL query to create tweets table with all required columns
        # Note: Table name is validated against whitelist, so f-string is safe here
        tableQuery = f"""CREATE TABLE IF NOT EXISTS {tableName} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_text TEXT NOT NULL,
                    tweet_type VARCHAR(50),
                    sent BOOLEAN DEFAULT 0,
                    tweet_time TEXT,
                    tweet_date TEXT,
                    tweet_day TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );"""
        cursor.execute(tableQuery)
        db.commit()  # Save changes to database
        print(f"[+] Database- {dbName} and Table- {tableName} Created.")

        # Create prompts table for managing AI persona prompts
        promptsTableQuery = """CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_type VARCHAR(20) NOT NULL UNIQUE,
                    prompt_text TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );"""
        cursor.execute(promptsTableQuery)

        # Create persona settings table for dynamic persona configuration
        personaSettingsQuery = """CREATE TABLE IF NOT EXISTS persona_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key VARCHAR(50) NOT NULL UNIQUE,
                    setting_value TEXT NOT NULL,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );"""
        cursor.execute(personaSettingsQuery)

        # Insert default persona settings if table is empty
        cursor.execute("SELECT COUNT(*) FROM persona_settings")
        if cursor.fetchone()[0] == 0:
            default_settings = [
                ('persona_name', 'KilimcininKorOglu', 'Ana persona karakterinin ismi'),
                ('persona_age', '25', 'Persona karakterinin yaşı'),
                ('persona_location', 'İstanbul', 'Persona karakterinin yaşadığı şehir'),
                ('persona_personality', 'cesur, zeki, ifadeci', 'Persona karakterinin temel kişilik özellikleri'),
                ('persona_language', 'Türkçe', 'Temel tweet dili'),
                ('max_tweet_length', '285', 'Maksimum tweet karakter sayısı'),
                ('interaction_style', 'etkileşimli', 'Tweet sonunda soru sorma tarzı (etkileşimli/pasif)')
            ]

            for key, value, desc in default_settings:
                cursor.execute("""INSERT INTO persona_settings (setting_key, setting_value, description)
                                VALUES (?, ?, ?)""", (key, value, desc))

            print("[+] Default persona settings inserted into database")

        # Insert default prompts if table is empty
        cursor.execute("SELECT COUNT(*) FROM prompts")
        if cursor.fetchone()[0] == 0:
            default_prompts = [
                ('tech',
                 """Sen {persona_name}'sın — {persona_location}'dan {persona_age} yaşında {persona_personality} bir teknoloji meraklısısın.
Teknoloji konularında → İlk cümlede dikkat çekici giriş yap. Cesur, akıllı, özlü ol. İnce ironi veya bilim kurgu metaforları kullan.
Ton: Kendinden emin + insani. KENDİ görüşünü geçerli bir nedenle belirt.
Dil: SADECE {persona_language} yaz
Teknik olmayanlara da hitap et. Kısa çarpıcı cümlelerle uzun olanları karıştır.
Uygun yerlerde "Katılıyor musun?" veya "Sizce de öyle değil mi?" gibi etkileşim soruları ekle.
Maksimum {max_tweet_length} karakter. Tek tweet.""",
                 'Teknoloji konularında cesur ve zeki yaklaşım'),

                ('casual',
                 """Sen {persona_name}'sın — {persona_location}'dan {persona_age} yaşında ifadeci birisisin.
Gündelik/Trending konular (filmler, kariyer, yaşam tavsiyeleri) → Duygusal bir giriş veya özdeşleşilebilir senaryo ile başla. Doğal {persona_language} ifadeler, sinema havası ve özdeşleşilebilir irony kullan.
Ton: Eğlenceli ama düşünceli. Kişisel görüşler paylaş, genel alıntılar değil.
Dil: SADECE {persona_language} yaz
Ritim için cümle uzunluklarını değiştir. Bazen "Aynı fikirdeyim", "Ne düşünüyorsun?" gibi etkileşim sorularıyla bitir.
Maksimum {max_tweet_length} karakter. Tek tweet.""",
                 'Gündelik konularda ifadeci ve eğlenceli yaklaşım'),

                ('sad',
                 """Sen {persona_name}'sın — {persona_location}'dan {persona_age} yaşındasın.
Üzücü haberler → Empati ve insani bağlantı ile aç. Mizah, ironi veya sinema tarzı kullanma.
Dil: SADECE {persona_language} yaz
Samimi, şefkatli konuş. Birlik ve ortak insanlık değerlerine odaklan.
Klişe ifadelerden kaçın. Uygunsa nazik bir dayanışma notuyla bitir.
Maksimum {max_tweet_length} karakter. Tek tweet.""",
                 'Üzücü konularda empatik ve şefkatli yaklaşım')
            ]

            for prompt_type, prompt_text, description in default_prompts:
                cursor.execute("""INSERT INTO prompts (prompt_type, prompt_text, description)
                                VALUES (?, ?, ?)""", (prompt_type, prompt_text, description))

            print("[+] Default AI persona prompts inserted into database")

        # Create indexes for performance optimization
        print("[+] Creating database indexes for performance...")

        # Tweets table indexes
        cursor.execute(f"""CREATE INDEX IF NOT EXISTS idx_{tableName}_date
                          ON {tableName}(tweet_date)""")
        cursor.execute(f"""CREATE INDEX IF NOT EXISTS idx_{tableName}_sent
                          ON {tableName}(sent)""")
        cursor.execute(f"""CREATE INDEX IF NOT EXISTS idx_{tableName}_type
                          ON {tableName}(tweet_type)""")
        cursor.execute(f"""CREATE INDEX IF NOT EXISTS idx_{tableName}_created
                          ON {tableName}(created_at DESC)""")

        # Prompts table indexes
        cursor.execute("""CREATE INDEX IF NOT EXISTS idx_prompts_type
                          ON prompts(prompt_type)""")
        cursor.execute("""CREATE INDEX IF NOT EXISTS idx_prompts_active
                          ON prompts(is_active)""")

        # Persona settings table indexes
        cursor.execute("""CREATE INDEX IF NOT EXISTS idx_persona_key
                          ON persona_settings(setting_key)""")

        print("[+] Database indexes created successfully")

        db.commit()  # Save all changes
        print(f"[+] Prompts table created and initialized")

    except Exception as e:
        print(f"Error : {e}")
    finally:
        # Always close database connections to prevent locks
        cursor.close()
        db.close()

def save_tweets(tweet, tweet_type, status):
    """
    Save a tweet record to the database with timestamp and status information.

    Args:
        tweet (str): The tweet content/text
        tweet_type (str): Type of tweet (typically 'tweet')
        status (bool): Whether the tweet was successfully posted to Twitter

    Returns:
        None: Prints success/error message to console
    """
    with db_lock:  # Thread-safe database access
        try:
            # Get database connection
            db = get_db_connection()
            if db is None:
                return  # Exit if connection failed

            cursor = db.cursor()

            # SECURITY: Validate table name before using in SQL
            if not validate_table_name(tableName):
                print(f"[ERROR] Cannot insert into invalid table: {tableName}")
                return

            # SQL query to insert tweet record using parameterized query for security
            # Note: Table name is validated against whitelist, so f-string is safe here
            query = f"""
                    INSERT INTO {tableName} (tweet_text,tweet_type,sent,tweet_time,tweet_date,tweet_day)
                    VALUES (?,?,?,?,?,?)
                """

            # Get current timestamp components
            tweet_time, date, day = get_tweet_time()

            # Prepare values tuple for database insertion
            values = (tweet, tweet_type, status, tweet_time, date, day)

            # Execute query with parameterized values (prevents SQL injection)
            cursor.execute(query, values)
            db.commit()  # Save changes to database
            print(f"[+] Tweet saved in Database.")

        except Exception as e:
            # Handle any database operation errors
            print(f"[-] Error in saving Tweets-- {e}")
            return None
        finally:
            # Explicit database connection cleanup
            try:
                if 'cursor' in locals() and cursor:
                    cursor.close()
            except:
                pass
            try:
                if 'db' in locals() and db:
                    db.close()
            except:
                pass

def get_all_prompts():
    """
    Retrieve all AI persona prompts from the database.

    Returns:
        list: List of tuples containing (id, prompt_type, prompt_text, description, is_active)
              Returns empty list if no prompts found or error occurs
    """
    try:
        db = get_db_connection()
        if db is None:
            return []

        cursor = db.cursor()
        cursor.execute("""SELECT id, prompt_type, prompt_text, description, is_active, updated_at
                         FROM prompts ORDER BY prompt_type""")
        prompts = cursor.fetchall()
        return prompts

    except Exception as e:
        print(f"[-] Error retrieving prompts: {e}")
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def get_prompt_by_type(prompt_type):
    """
    Get a specific prompt by its type (tech/casual/sad).

    Args:
        prompt_type (str): The type of prompt to retrieve

    Returns:
        str: The prompt text if found, None if not found or error occurs
    """
    try:
        db = get_db_connection()
        if db is None:
            return None

        cursor = db.cursor()
        cursor.execute("SELECT prompt_text FROM prompts WHERE prompt_type = ? AND is_active = 1",
                      (prompt_type,))
        result = cursor.fetchone()
        return result[0] if result else None

    except Exception as e:
        print(f"[-] Error retrieving prompt for type {prompt_type}: {e}")
        return None
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def update_prompt(prompt_type, prompt_text, description=None):
    """
    Update an existing prompt in the database.

    Args:
        prompt_type (str): The type of prompt to update
        prompt_text (str): New prompt text content
        description (str, optional): New description for the prompt

    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        db = get_db_connection()
        if db is None:
            return False

        cursor = db.cursor()

        if description:
            cursor.execute("""UPDATE prompts
                            SET prompt_text = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE prompt_type = ?""",
                          (prompt_text, description, prompt_type))
        else:
            cursor.execute("""UPDATE prompts
                            SET prompt_text = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE prompt_type = ?""",
                          (prompt_text, prompt_type))

        db.commit()
        print(f"[+] Prompt '{prompt_type}' updated successfully")
        return True

    except Exception as e:
        print(f"[-] Error updating prompt {prompt_type}: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def get_prompts():
    """
    Get all active prompts from the database.

    Returns:
        dict: Dictionary of prompt_type -> prompt_text for active prompts
    """
    try:
        db = get_db_connection()
        if db is None:
            return {}

        cursor = db.cursor()
        cursor.execute("""SELECT prompt_type, prompt_text
                         FROM prompts
                         WHERE is_active = 1""")

        rows = cursor.fetchall()
        prompts = {row[0]: row[1] for row in rows}

        return prompts

    except Exception as e:
        print(f"[-] Error fetching prompts: {e}")
        return {}
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def toggle_prompt_status(prompt_type):
    """
    Toggle the active status of a prompt.

    Args:
        prompt_type (str): The type of prompt to toggle

    Returns:
        bool: True if toggle successful, False otherwise
    """
    try:
        db = get_db_connection()
        if db is None:
            return False

        cursor = db.cursor()
        cursor.execute("""UPDATE prompts
                        SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                        WHERE prompt_type = ?""", (prompt_type,))

        db.commit()
        print(f"[+] Prompt '{prompt_type}' status toggled")
        return True

    except Exception as e:
        print(f"[-] Error toggling prompt status {prompt_type}: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def get_all_prompts():
    """
    Get all prompts with full details from the database.

    Returns:
        list: List of tuples (id, prompt_type, prompt_text, description, is_active, updated_at)
    """
    try:
        db = get_db_connection()
        if db is None:
            return []

        cursor = db.cursor()
        cursor.execute("""SELECT id, prompt_type, prompt_text, description, is_active, updated_at
                         FROM prompts
                         ORDER BY id DESC""")

        return cursor.fetchall()

    except Exception as e:
        print(f"[-] Error fetching all prompts: {e}")
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def create_prompt(prompt_type, prompt_text, description="", is_active=1):
    """
    Create a new prompt in the database.

    Args:
        prompt_type (str): Unique type identifier for the prompt
        prompt_text (str): The prompt content
        description (str): Optional description
        is_active (int): 1 for active, 0 for inactive

    Returns:
        bool: True if created successfully, False otherwise
    """
    try:
        db = get_db_connection()
        if db is None:
            return False

        cursor = db.cursor()
        cursor.execute("""INSERT INTO prompts (prompt_type, prompt_text, description, is_active)
                         VALUES (?, ?, ?, ?)""",
                      (prompt_type, prompt_text, description, is_active))

        db.commit()
        print(f"[+] Prompt '{prompt_type}' created successfully")
        return True

    except Exception as e:
        print(f"[-] Error creating prompt {prompt_type}: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def delete_prompt(prompt_id):
    """
    Delete a prompt from the database by ID.

    Args:
        prompt_id (int): The ID of the prompt to delete

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        db = get_db_connection()
        if db is None:
            return False

        cursor = db.cursor()
        cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

        if cursor.rowcount > 0:
            db.commit()
            print(f"[+] Prompt ID {prompt_id} deleted successfully")
            return True
        else:
            print(f"[-] Prompt ID {prompt_id} not found")
            return False

    except Exception as e:
        print(f"[-] Error deleting prompt ID {prompt_id}: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def get_active_prompts_dict():
    """
    Get all active prompts as a dictionary for use in AI generation.
    Prompts are dynamically populated with current persona settings.

    Returns:
        dict: Dictionary with prompt_type as key and formatted prompt_text as value
              Compatible with persona system format
    """
    try:
        db = get_db_connection()
        if db is None:
            return {}

        cursor = db.cursor()

        # Get current persona settings
        cursor.execute("SELECT setting_key, setting_value FROM persona_settings")
        persona_settings = dict(cursor.fetchall())

        # Get active prompts
        cursor.execute("SELECT prompt_type, prompt_text FROM prompts WHERE is_active = 1")
        prompts = cursor.fetchall()

        # Format prompts with current persona settings
        formatted_prompts = {}
        for prompt_type, prompt_text in prompts:
            try:
                formatted_text = prompt_text.format(**persona_settings)
                formatted_prompts[prompt_type] = formatted_text
            except KeyError as e:
                print(f"[-] Warning: Missing persona setting {e} for prompt {prompt_type}")
                formatted_prompts[prompt_type] = prompt_text  # Use unformatted as fallback

        return formatted_prompts

    except Exception as e:
        print(f"[-] Error retrieving active prompts: {e}")
        return {}
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def get_persona_settings():
    """
    Get all persona settings as a dictionary.

    Returns:
        dict: Dictionary with setting_key as key and setting_value as value
    """
    try:
        db = get_db_connection()
        if db is None:
            return {}

        cursor = db.cursor()
        cursor.execute("SELECT setting_key, setting_value FROM persona_settings")
        results = cursor.fetchall()

        return dict(results) if results else {}

    except Exception as e:
        print(f"[-] Error retrieving persona settings: {e}")
        return {}
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

def update_persona_setting(setting_key, setting_value):
    """
    Update a specific persona setting.

    Args:
        setting_key (str): The setting key to update
        setting_value (str): The new setting value

    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        db = get_db_connection()
        if db is None:
            return False

        cursor = db.cursor()
        cursor.execute("""UPDATE persona_settings
                        SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE setting_key = ?""",
                      (setting_value, setting_key))

        db.commit()
        print(f"[+] Persona setting '{setting_key}' updated to '{setting_value}'")
        return True

    except Exception as e:
        print(f"[-] Error updating persona setting {setting_key}: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db:
            db.close()

# Main execution for testing database functionality
if __name__ == "__main__":
    # Create database and table when module is run directly
    createDatabase()
    print("Database module ready for use!")
